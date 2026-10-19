from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


# Pin the first image release with native lossy WebP encoding plus the 4.10.2
# JPEG safety fixes. Keep it exact so this portable build remains reproducible.
replace_once(
    'pubspec.yaml',
    '  image: ^4.9.2\n',
    '  image: 4.10.2\n',
    'pin-image-4.10.2-for-lossy-webp',
)


# Windows visual-cache v3:
# - gallery thumbnails are converted once to <=512px lossy WebP;
# - conversion is limited to two background isolates;
# - AVIF/animated previews stay in their original bytes so their dedicated
#   decoders keep receiving the format they expect;
# - samples remain source bytes for compatibility, but Windows gallery no longer
#   selects samples and the full-res viewer stays memory-only;
# - v2 thumbnail rows are discarded once so they can be rebuilt as WebP.
compressed_cache = r'''import 'dart:async';
import 'dart:collection';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import 'package:sqflite/sqflite.dart';

import 'package:lolisnatcher/src/handlers/service_handler.dart';

bool _startsWithBytes(Uint8List bytes, List<int> signature) {
  if (bytes.length < signature.length) return false;
  for (int i = 0; i < signature.length; i++) {
    if (bytes[i] != signature[i]) return false;
  }
  return true;
}

bool _containsBytes(Uint8List bytes, List<int> token, {required int scanLimit}) {
  if (bytes.length < token.length) return false;
  final int end = bytes.length < scanLimit ? bytes.length : scanLimit;
  for (int i = 0; i <= end - token.length; i++) {
    bool matched = true;
    for (int j = 0; j < token.length; j++) {
      if (bytes[i + j] != token[j]) {
        matched = false;
        break;
      }
    }
    if (matched) return true;
  }
  return false;
}

bool _mustKeepThumbnailSourceFormat(Uint8List bytes) {
  // GIF thumbnails can be animated; preserve animation instead of flattening.
  if (_startsWithBytes(bytes, const <int>[0x47, 0x49, 0x46, 0x38])) {
    return true;
  }

  // CustomNetworkAvifImage validates the AVIF magic after loading, so AVIF
  // payloads must never be replaced with WebP bytes underneath that provider.
  final bool isIsoBmff = _containsBytes(
    bytes,
    const <int>[0x66, 0x74, 0x79, 0x70], // ftyp
    scanLimit: 16,
  );
  if (isIsoBmff &&
      (_containsBytes(bytes, const <int>[0x61, 0x76, 0x69, 0x66], scanLimit: 48) || // avif
          _containsBytes(bytes, const <int>[0x61, 0x76, 0x69, 0x73], scanLimit: 48))) {
    // avis
    return true;
  }

  // Animated WebP contains an ANIM chunk near the beginning. Keep it animated.
  if (_containsBytes(bytes, const <int>[0x41, 0x4e, 0x49, 0x4d], scanLimit: 96)) {
    return true;
  }

  return false;
}

Uint8List? _encodeVisualThumbnailWebP(Map<String, Object> args) {
  final Uint8List bytes = args['bytes']! as Uint8List;
  final int maxDimension = args['maxDimension']! as int;

  try {
    if (_mustKeepThumbnailSourceFormat(bytes)) {
      return null;
    }

    img.Image? decoded = img.decodeImage(bytes);
    if (decoded == null || decoded.numFrames != 1) {
      return null;
    }

    if (decoded.width > maxDimension || decoded.height > maxDimension) {
      decoded = decoded.width >= decoded.height
          ? img.copyResize(
              decoded,
              width: maxDimension,
              interpolation: img.Interpolation.linear,
            )
          : img.copyResize(
              decoded,
              height: maxDimension,
              interpolation: img.Interpolation.linear,
            );
    }

    return img.encodeWebP(
      decoded,
      lossless: false,
      quality: 74,
      method: 2,
      alphaQuality: 82,
      exact: false,
      singleFrame: true,
    );
  } catch (_) {
    return null;
  }
}

class _WebPJob {
  _WebPJob(this.bytes, this.maxDimension, this.completer);

  final Uint8List bytes;
  final int maxDimension;
  final Completer<Uint8List?> completer;
}

class _WebPQueue {
  static const int _maxParallel = 2;
  static final Queue<_WebPJob> _pending = Queue<_WebPJob>();
  static int _active = 0;

  static Future<Uint8List?> encode(Uint8List bytes, {required int maxDimension}) {
    final Completer<Uint8List?> completer = Completer<Uint8List?>();
    _pending.add(_WebPJob(bytes, maxDimension, completer));
    _pump();
    return completer.future;
  }

  static void _pump() {
    while (_active < _maxParallel && _pending.isNotEmpty) {
      final _WebPJob job = _pending.removeFirst();
      _active++;
      unawaited(_run(job));
    }
  }

  static Future<void> _run(_WebPJob job) async {
    try {
      final Uint8List? result = await compute(
        _encodeVisualThumbnailWebP,
        <String, Object>{
          'bytes': job.bytes,
          'maxDimension': job.maxDimension,
        },
      );
      job.completer.complete(result);
    } catch (_) {
      job.completer.complete(null);
    } finally {
      _active--;
      _pump();
    }
  }
}

/// Windows portable thumbnail/sample cache.
///
/// Gallery thumbnails are stored as small lossy WebP images in one SQLite DB.
/// The full-resolution viewer never uses this cache: it loads the original
/// remote file into memory and keeps its real format/bytes intact.
class CompressedVisualCache {
  CompressedVisualCache._();

  static final CompressedVisualCache instance = CompressedVisualCache._();

  Future<Database>? _databaseFuture;

  static bool isVisualFolder(String? folder) => folder == 'thumbnails' || folder == 'samples';

  Future<String> _rootPath() async => ServiceHandler.getCacheDir();

  Future<String> get databasePath async => '${await _rootPath()}visual_cache.db';

  String _key(String folder, String legacyPath) {
    final String fileName = legacyPath.split(Platform.pathSeparator).last;
    return '$folder|$fileName';
  }

  Future<Database> _database() {
    return _databaseFuture ??= _openDatabase();
  }

  Future<Database> _openDatabase() async {
    final String path = await databasePath;
    await File(path).parent.create(recursive: true);
    final Database db = await databaseFactory.openDatabase(
      path,
      options: OpenDatabaseOptions(
        version: 3,
        onConfigure: (db) async {
          await db.execute('PRAGMA journal_mode=WAL;');
          await db.execute('PRAGMA synchronous=NORMAL;');
        },
        onUpgrade: (db, oldVersion, newVersion) async {
          if (oldVersion < 2) {
            await db.delete(
              'VisualCache',
              where: 'compressed = ?',
              whereArgs: <Object?>[1],
            );
          }
          if (oldVersion < 3) {
            final List<Map<String, Object?>> columns = await db.rawQuery('PRAGMA table_info(VisualCache)');
            final bool hasCodec = columns.any((row) => row['name'] == 'codec');
            if (!hasCodec) {
              await db.execute("ALTER TABLE VisualCache ADD COLUMN codec TEXT NOT NULL DEFAULT 'source'");
            }
            // Rebuild old Windows gallery thumbnails in the new WebP format.
            await db.delete(
              'VisualCache',
              where: 'folder = ?',
              whereArgs: <Object?>['thumbnails'],
            );
          }
        },
        onCreate: (db, version) async {
          await db.execute(
            'CREATE TABLE VisualCache ('
            'cache_key TEXT PRIMARY KEY, '
            'folder TEXT NOT NULL, '
            'payload BLOB NOT NULL, '
            'compressed INTEGER NOT NULL, '
            'codec TEXT NOT NULL, '
            'original_size INTEGER NOT NULL, '
            'stored_size INTEGER NOT NULL, '
            'created_at INTEGER NOT NULL, '
            'accessed_at INTEGER NOT NULL'
            ')',
          );
          await db.execute(
            'CREATE INDEX VisualCache_folder_accessed '
            'ON VisualCache(folder, accessed_at)',
          );
        },
      ),
    );
    return db;
  }

  Future<Uint8List?> read(String folder, String legacyPath) async {
    final Database db = await _database();
    final String cacheKey = _key(folder, legacyPath);
    final List<Map<String, Object?>> rows = await db.query(
      'VisualCache',
      columns: <String>['payload', 'accessed_at'],
      where: 'cache_key = ?',
      whereArgs: <Object?>[cacheKey],
      limit: 1,
    );

    if (rows.isNotEmpty) {
      final Object? raw = rows.first['payload'];
      final Uint8List payload = raw is Uint8List ? raw : Uint8List.fromList((raw as List).cast<int>());
      final int now = DateTime.now().millisecondsSinceEpoch;
      final int lastAccess = (rows.first['accessed_at'] as int?) ?? 0;
      if (now - lastAccess >= const Duration(minutes: 10).inMilliseconds) {
        await db.update(
          'VisualCache',
          <String, Object?>{'accessed_at': now},
          where: 'cache_key = ?',
          whereArgs: <Object?>[cacheKey],
        );
      }
      return payload;
    }

    // Lazy migration from older loose thumbnail/sample files.
    final File legacy = File(legacyPath);
    if (await legacy.exists()) {
      try {
        final Uint8List bytes = await legacy.readAsBytes();
        if (bytes.isNotEmpty) {
          final Uint8List cachedBytes = await write(folder, legacyPath, bytes);
          await legacy.delete();
          return cachedBytes;
        }
      } catch (_) {}
    }
    return null;
  }

  /// Stores a visual-cache entry and returns the exact bytes that should be
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

  Future<void> delete(String folder, String legacyPath) async {
    final Database db = await _database();
    await db.delete(
      'VisualCache',
      where: 'cache_key = ?',
      whereArgs: <Object?>[_key(folder, legacyPath)],
    );
    final File legacy = File(legacyPath);
    if (await legacy.exists()) {
      try {
        await legacy.delete();
      } catch (_) {}
    }
  }

  Future<Map<String, int>> getStats(String folder) async {
    final Database db = await _database();
    final List<Map<String, Object?>> rows = await db.rawQuery(
      'SELECT COUNT(*) AS entries, COALESCE(SUM(stored_size), 0) AS bytes '
      'FROM VisualCache WHERE folder = ?',
      <Object?>[folder],
    );
    int count = (rows.first['entries'] as int?) ?? 0;
    int total = (rows.first['bytes'] as int?) ?? 0;

    final Directory legacyDir = Directory('${await _rootPath()}$folder');
    if (await legacyDir.exists()) {
      await for (final FileSystemEntity entity in legacyDir.list(recursive: true, followLinks: false)) {
        if (entity is! File) continue;
        try {
          final int size = await entity.length();
          if (size > 0 && !entity.path.contains('.temp_')) {
            count++;
            total += size;
          }
        } catch (_) {}
      }
    }
    return <String, int>{'fileNum': count, 'totalSize': total};
  }

  Future<void> clearFolder(String folder) async {
    final Database db = await _database();
    await db.delete('VisualCache', where: 'folder = ?', whereArgs: <Object?>[folder]);
    final Directory legacyDir = Directory('${await _rootPath()}$folder');
    if (await legacyDir.exists()) {
      try {
        await legacyDir.delete(recursive: true);
      } catch (_) {}
    }
    try {
      await db.execute('PRAGMA wal_checkpoint(TRUNCATE);');
      await db.execute('VACUUM;');
    } catch (_) {}
  }

  Future<void> cleanup({required Duration maxAge, required int maxBytes}) async {
    final Database db = await _database();
    if (maxAge > Duration.zero) {
      final int cutoff = DateTime.now().subtract(maxAge).millisecondsSinceEpoch;
      await db.delete('VisualCache', where: 'accessed_at < ?', whereArgs: <Object?>[cutoff]);
    }

    if (maxBytes > 0) {
      final List<Map<String, Object?>> rows = await db.rawQuery(
        'SELECT COALESCE(SUM(stored_size), 0) AS bytes FROM VisualCache',
      );
      int current = (rows.first['bytes'] as int?) ?? 0;
      if (current > maxBytes) {
        final List<Map<String, Object?>> oldest = await db.query(
          'VisualCache',
          columns: <String>['cache_key', 'stored_size'],
          orderBy: 'accessed_at ASC',
        );
        final Batch batch = db.batch();
        for (final row in oldest) {
          if (current <= maxBytes) break;
          batch.delete('VisualCache', where: 'cache_key = ?', whereArgs: <Object?>[row['cache_key']]);
          current -= (row['stored_size'] as int?) ?? 0;
        }
        await batch.commit(noResult: true);
      }
    }
  }
}
'''
Path('lib/src/services/compressed_visual_cache.dart').write_text(compressed_cache, encoding='utf-8')
print('REPLACED visual cache with WebP thumbnail cache v3')


# Make the first network miss decode the reduced WebP payload too, rather than
# writing WebP to DB but returning the original source bytes for first display.
replace_once(
    'lib/src/widgets/image/custom_network_image.dart',
    """      await CompressedVisualCache.instance.write(cacheFolder!, cacheFilePath, bytes);
      return bytes;
""",
    """      return await CompressedVisualCache.instance.write(
        cacheFolder!,
        cacheFilePath,
        bytes,
      );
""",
    'display-newly-cached-webp-immediately',
)


# Windows grid: prefer the booru thumbnail and never choose the larger sample
# when a real thumbnail URL exists. If a provider has no thumbnail URL, keep the
# upstream sample fallback rather than trying to load an empty URL.
replace_once(
    'lib/src/widgets/thumbnail/thumbnail.dart',
    """    isThumbQuality =
        settingsHandler.previewMode.isThumbnail ||
""",
    """    isThumbQuality =
        (Platform.isWindows && widget.item.thumbnailURL.isNotEmpty) ||
        settingsHandler.previewMode.isThumbnail ||
""",
    'windows-grid-thumbnail-only',
)


# Windows viewer: prefer the real original file URL/format whenever it is known.
# If fileURL is absent, preserve upstream sample behavior instead of failing an
# otherwise viewable post. The v8 viewer patch already disables persistent media
# caching for imageFolder == 'media', so original bytes stay memory-only.
replace_once(
    'lib/src/widgets/image/image_viewer.dart',
    """  bool get useFullImage => settingsHandler.galleryMode.isFullRes
      ? !widget.booruItem.toggleQuality.value
      : widget.booruItem.toggleQuality.value;
""",
    """  bool get useFullImage => Platform.isWindows && widget.booruItem.fileURL.isNotEmpty
      ? true
      : settingsHandler.galleryMode.isFullRes
          ? !widget.booruItem.toggleQuality.value
          : widget.booruItem.toggleQuality.value;
""",
    'windows-viewer-original-format-memory-only',
)


# Describe the actual persistent cache rather than the old zlib implementation.
replace_once(
    'lib/src/pages/settings/save_cache_page.dart',
    r"Cache visual empaquetada (modo rapido): Data\LoliSnatcher\cache\visual_cache.db",
    r"Miniaturas WebP empaquetadas: Data\LoliSnatcher\cache\visual_cache.db",
    'webp-cache-settings-label',
)


# Guards.
cache_text = Path('lib/src/services/compressed_visual_cache.dart').read_text(encoding='utf-8')
thumb_text = Path('lib/src/widgets/thumbnail/thumbnail.dart').read_text(encoding='utf-8')
viewer_text = Path('lib/src/widgets/image/image_viewer.dart').read_text(encoding='utf-8')
pubspec_text = Path('pubspec.yaml').read_text(encoding='utf-8')

checks = {
    'image 4.10.2 pinned': '  image: 4.10.2\n' in pubspec_text,
    'cache db v3': 'version: 3' in cache_text,
    'lossy webp encoder': 'lossless: false' in cache_text and 'quality: 74' in cache_text,
    'thumbnail max dimension': 'maxDimension: 512' in cache_text,
    'two conversion workers': 'static const int _maxParallel = 2;' in cache_text,
    'avif source preservation': '_mustKeepThumbnailSourceFormat' in cache_text and '0x61, 0x76, 0x69, 0x66' in cache_text,
    'windows thumbnail grid': '(Platform.isWindows && widget.item.thumbnailURL.isNotEmpty)' in thumb_text,
    'windows original viewer': 'Platform.isWindows && widget.booruItem.fileURL.isNotEmpty' in viewer_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.2 guard failed: {label}')

print('V8_2_WEBP_THUMBNAIL_CACHE=PASS')
print('V8_2_WEBP_MAX_DIMENSION=512')
print('V8_2_WEBP_QUALITY=74')
print('V8_2_WEBP_WORKERS=2')
print('V8_2_AVIF_ANIMATION_FALLBACK=PASS')
print('V8_2_WINDOWS_GRID_THUMBNAIL_PREFERRED=PASS')
print('V8_2_WINDOWS_VIEWER_ORIGINAL_MEMORY_ONLY=PASS')
