from pathlib import Path

cache = Path('lib/src/services/compressed_visual_cache.dart')
text = cache.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.9 {label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)
    print(f'PATCHED v8.9 {label}')


# Keep WebP conversion serialized. The old two-worker path could run two image
# decodes/resizes/encodes simultaneously while Flutter was also decoding visible
# tiles, causing short CPU saturation spikes on Windows.
replace_once(
    '  static const int _maxParallel = 2;\n',
    '  static const int _maxParallel = 1;\n',
    'single-webp-worker',
)

# Cache-hit LRU maintenance must never delay delivery of an already-cached image.
# Keep the 10-minute throttle from v8.1, but perform the timestamp touch in the
# background instead of awaiting the SQLite write on the image load path.
replace_once(
    """      if (now - lastAccess >= const Duration(minutes: 10).inMilliseconds) {
        await db.update(
          'VisualCache',
          <String, Object?>{'accessed_at': now},
          where: 'cache_key = ?',
          whereArgs: <Object?>[cacheKey],
        );
      }
      return payload;
""",
    """      if (now - lastAccess >= const Duration(minutes: 10).inMilliseconds) {
        unawaited(_touchAccessedAt(db, cacheKey, now));
      }
      return payload;
""",
    'nonblocking-lru-touch',
)

# Add a small helper and a dedup set for background thumbnail persistence.
replace_once(
    """  Future<Database>? _databaseFuture;

  static bool isVisualFolder(String? folder) => folder == 'thumbnails' || folder == 'samples';
""",
    """  Future<Database>? _databaseFuture;
  final Set<String> _backgroundThumbnailWrites = <String>{};

  static bool isVisualFolder(String? folder) => folder == 'thumbnails' || folder == 'samples';
""",
    'background-write-dedup-state',
)

replace_once(
    """  Future<Database> _database() {
    return _databaseFuture ??= _openDatabase();
  }

  Future<Database> _openDatabase() async {
""",
    """  Future<Database> _database() {
    return _databaseFuture ??= _openDatabase();
  }

  Future<void> _touchAccessedAt(Database db, String cacheKey, int now) async {
    try {
      await db.update(
        'VisualCache',
        <String, Object?>{'accessed_at': now},
        where: 'cache_key = ?',
        whereArgs: <Object?>[cacheKey],
      );
    } catch (_) {}
  }

  Future<Database> _openDatabase() async {
""",
    'lru-touch-helper',
)

old_write = """  /// Stores a visual-cache entry and returns the exact bytes that should be
  /// decoded for display. This makes the first uncached gallery load use the
  /// same reduced WebP bytes that subsequent cache hits use.
  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    if (bytes.isEmpty) return bytes;

    Uint8List payload = bytes;
    String codec = 'source';

    if (folder == 'thumbnails') {
      final Uint8List? webp = await _WebPQueue.encode(bytes, maxDimension: 512);
      if (webp != null && webp.isNotEmpty) {
        payload = webp;
        codec = 'webp-lossy-q74-512';
      }
    }

    final Database db = await _database();
    final int now = DateTime.now().millisecondsSinceEpoch;
    await db.insert(
      'VisualCache',
      <String, Object?>{
        'cache_key': _key(folder, legacyPath),
        'folder': folder,
        'payload': payload,
        'compressed': 0,
        'codec': codec,
        'original_size': bytes.length,
        'stored_size': payload.length,
        'created_at': now,
        'accessed_at': now,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return payload;
  }
"""

new_write = """  Future<void> _storeEntry(
    String folder,
    String legacyPath,
    Uint8List sourceBytes,
    Uint8List payload,
    String codec,
  ) async {
    final Database db = await _database();
    final int now = DateTime.now().millisecondsSinceEpoch;
    await db.insert(
      'VisualCache',
      <String, Object?>{
        'cache_key': _key(folder, legacyPath),
        'folder': folder,
        'payload': payload,
        'compressed': 0,
        'codec': codec,
        'original_size': sourceBytes.length,
        'stored_size': payload.length,
        'created_at': now,
        'accessed_at': now,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> _persistThumbnailInBackground(
    String folder,
    String legacyPath,
    Uint8List bytes,
  ) async {
    final String cacheKey = _key(folder, legacyPath);
    if (!_backgroundThumbnailWrites.add(cacheKey)) return;

    try {
      Uint8List payload = bytes;
      String codec = 'source';
      final Uint8List? webp = await _WebPQueue.encode(bytes, maxDimension: 512);
      if (webp != null && webp.isNotEmpty) {
        payload = webp;
        codec = 'webp-lossy-q74-512';
      }
      await _storeEntry(folder, legacyPath, bytes, payload, codec);
    } catch (_) {
      // Cache persistence is optional. A failed background conversion/write must
      // never block or fail the visible image load.
    } finally {
      _backgroundThumbnailWrites.remove(cacheKey);
    }
  }

  /// Store visual-cache data without putting CPU/SQLite work on the visible
  /// thumbnail load path. A new thumbnail is displayed immediately from the
  /// downloaded source bytes; its <=512px WebP representation is persisted in
  /// the background and will be used on subsequent cache hits.
  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    if (bytes.isEmpty) return bytes;

    if (folder == 'thumbnails') {
      unawaited(_persistThumbnailInBackground(folder, legacyPath, bytes));
      return bytes;
    }

    await _storeEntry(folder, legacyPath, bytes, bytes, 'source');
    return bytes;
  }
"""

replace_once(old_write, new_write, 'display-first-background-webp-cache')

cache.write_text(text, encoding='utf-8')

final = cache.read_text(encoding='utf-8')
checks = {
    'single WebP worker': 'static const int _maxParallel = 1;' in final,
    'display-first thumbnail path': "unawaited(_persistThumbnailInBackground(folder, legacyPath, bytes));" in final,
    'background WebP persistence': '_persistThumbnailInBackground' in final and "codec = 'webp-lossy-q74-512';" in final,
    'deduplicated background writes': '_backgroundThumbnailWrites.add(cacheKey)' in final,
    'nonblocking LRU': 'unawaited(_touchAccessedAt(db, cacheKey, now));' in final,
    'no synchronous thumbnail encode': "if (folder == 'thumbnails') {\n      final Uint8List? webp = await _WebPQueue.encode" not in final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.9 guard failed: {label}')

print('V8_9_DISPLAY_FIRST_THUMBNAILS=PASS')
print('V8_9_BACKGROUND_WEBP_CACHE=PASS')
print('V8_9_SINGLE_WEBP_WORKER=PASS')
print('V8_9_NONBLOCKING_LRU=PASS')
print('V8_9_GALLERY_FREEZE_HOTFIX=PASS')
