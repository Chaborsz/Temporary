from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


# ---------------------------------------------------------------------------
# v8.1 Windows image-load CPU hotfix.
#
# The v8 packed cache tried zlib level 9 for every thumbnail/sample miss, even
# though JPEG/PNG/WebP/AVIF payloads are already compressed. A grid can start
# many image loads at once, so the compression isolates plus SQLite writes can
# saturate CPU. Keep the same SQLite container/schema compatibility, but store
# new visual-cache payloads raw and only refresh LRU timestamps periodically.
# Existing compressed v8 rows are discarded once by the DB v2 migration so a
# newly-updated build cannot immediately hit a decompression storm.
# ---------------------------------------------------------------------------
cache = 'lib/src/services/compressed_visual_cache.dart'

replace_once(
    cache,
    """Uint8List _zlibCompressVisualCache(Uint8List bytes) {
  return Uint8List.fromList(ZLibEncoder(level: 9).convert(bytes));
}

""",
    "",
    'remove-per-image-level9-compressor',
)

replace_once(
    cache,
    """        version: 1,
        onConfigure: (db) async {
""",
    """        version: 2,
        onConfigure: (db) async {
""",
    'visual-cache-db-v2',
)

replace_once(
    cache,
    """        onCreate: (db, version) async {
""",
    """        onUpgrade: (db, oldVersion, newVersion) async {
          if (oldVersion < 2) {
            await db.delete(
              'VisualCache',
              where: 'compressed = ?',
              whereArgs: <Object?>[1],
            );
          }
        },
        onCreate: (db, version) async {
""",
    'drop-old-compressed-v8-rows-once',
)

replace_once(
    cache,
    """      columns: <String>['payload', 'compressed'],
""",
    """      columns: <String>['payload', 'compressed', 'accessed_at'],
""",
    'read-access-timestamp',
)

replace_once(
    cache,
    """      await db.update(
        'VisualCache',
        <String, Object?>{'accessed_at': DateTime.now().millisecondsSinceEpoch},
        where: 'cache_key = ?',
        whereArgs: <Object?>[cacheKey],
      );
      return bytes;
""",
    """      final int now = DateTime.now().millisecondsSinceEpoch;
      final int lastAccess = (rows.first['accessed_at'] as int?) ?? 0;
      if (now - lastAccess >= const Duration(minutes: 10).inMilliseconds) {
        await db.update(
          'VisualCache',
          <String, Object?>{'accessed_at': now},
          where: 'cache_key = ?',
          whereArgs: <Object?>[cacheKey],
        );
      }
      return bytes;
""",
    'throttle-cache-lru-writes',
)

replace_once(
    cache,
    """    final Uint8List compressedBytes = await compute(_zlibCompressVisualCache, bytes);
    final bool useCompressed = compressedBytes.length < bytes.length;
    final Uint8List payload = useCompressed ? compressedBytes : bytes;
""",
    """    // Image payloads are already compressed formats in normal use. Recompressing
    // each thumbnail/sample is CPU-expensive and usually saves nothing.
    final bool useCompressed = false;
    final Uint8List payload = bytes;
""",
    'store-new-visual-cache-raw',
)

# ---------------------------------------------------------------------------
# Windows grid decode hotfix.
#
# Upstream intentionally skips ResizeImage on desktop. On Windows this means a
# small grid tile may decode the source thumbnail/sample at its full pixel size.
# Enable target-size decoding on Windows and avoid the extra low-quality
# thumbnail request while a sample is already loading, cutting both decode work
# and simultaneous network/cache operations roughly in half for sample mode.
# ---------------------------------------------------------------------------
thumbnail = 'lib/src/widgets/thumbnail/thumbnail.dart'

replace_once(
    thumbnail,
    "import 'dart:async';\n",
    "import 'dart:async';\nimport 'dart:io';\n",
    'thumbnail-windows-platform-import',
)

replace_once(
    thumbnail,
    """    final bool shouldResize = (thumbWidth != null || thumbHeight != null) && !PlatformExt.isDesktop;
""",
    """    final bool shouldResize =
        (thumbWidth != null || thumbHeight != null) &&
        (!PlatformExt.isDesktop || Platform.isWindows);
""",
    'windows-target-size-decode',
)

replace_once(
    thumbnail,
    """    useExtra.value = isThumbQuality == false && !widget.item.isHidden && !settingsHandler.shitDevice;
""",
    """    useExtra.value =
        isThumbQuality == false &&
        !widget.item.isHidden &&
        !settingsHandler.shitDevice &&
        !Platform.isWindows;
""",
    'disable-double-preview-load-on-windows',
)

# Keep the cache location accurate and rename it to describe the new fast path.
settings = Path('lib/src/pages/settings/save_cache_page.dart')
text = settings.read_text(encoding='utf-8')
old = r"Cache visual comprimida: Data\cache\visual_cache.db"
new = r"Cache visual empaquetada (modo rapido): Data\LoliSnatcher\cache\visual_cache.db"
count = text.count(old)
if count != 1:
    raise SystemExit(f'v8 cache path label: expected 1 match, found {count}')
settings.write_text(text.replace(old, new, 1), encoding='utf-8')

# Guards.
cache_text = Path(cache).read_text(encoding='utf-8')
thumb_text = Path(thumbnail).read_text(encoding='utf-8')
if 'version: 2' not in cache_text:
    raise SystemExit('V8.1 guard failed: DB v2 missing')
if 'final bool useCompressed = false;' not in cache_text:
    raise SystemExit('V8.1 guard failed: raw packed writes missing')
if 'Platform.isWindows' not in thumb_text or '!Platform.isWindows' not in thumb_text:
    raise SystemExit('V8.1 guard failed: Windows thumbnail limits missing')

print('V8_CACHE_PATH_LABEL=PASS')
print('V8_1_VISUAL_CACHE_CPU_FIX=PASS')
print('V8_1_WINDOWS_TARGET_SIZE_DECODE=PASS')
print('V8_1_WINDOWS_SINGLE_PREVIEW_LOAD=PASS')
