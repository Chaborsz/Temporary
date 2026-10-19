from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count} in {p}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED {label}: {p}")


def replace_count(path, old, new, expected, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} matches, found {count} in {p}")
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"PATCHED {label}: {p} ({count} matches)")


compressed_cache = r'''import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';

import 'package:lolisnatcher/src/handlers/service_handler.dart';

Uint8List _zlibCompressVisualCache(Uint8List bytes) {
  return Uint8List.fromList(ZLibEncoder(level: 9).convert(bytes));
}

Uint8List _zlibDecompressVisualCache(Uint8List bytes) {
  return Uint8List.fromList(ZLibDecoder().convert(bytes));
}

/// Windows portable thumbnail/sample cache.
///
/// Entries are packed into a single SQLite database instead of being exposed
/// as thousands of loose image files. Bytes are zlib-compressed only when that
/// actually makes the already-compressed source smaller; otherwise the exact
/// original bytes are stored to avoid cache inflation.
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
        version: 1,
        onConfigure: (db) async {
          await db.execute('PRAGMA journal_mode=WAL;');
          await db.execute('PRAGMA synchronous=NORMAL;');
        },
        onCreate: (db, version) async {
          await db.execute(
            'CREATE TABLE VisualCache ('
            'cache_key TEXT PRIMARY KEY, '
            'folder TEXT NOT NULL, '
            'payload BLOB NOT NULL, '
            'compressed INTEGER NOT NULL, '
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
      columns: <String>['payload', 'compressed'],
      where: 'cache_key = ?',
      whereArgs: <Object?>[cacheKey],
      limit: 1,
    );

    if (rows.isNotEmpty) {
      final Object? raw = rows.first['payload'];
      final Uint8List payload = raw is Uint8List ? raw : Uint8List.fromList((raw as List).cast<int>());
      final bool compressed = (rows.first['compressed'] as int? ?? 0) == 1;
      final Uint8List bytes = compressed ? await compute(_zlibDecompressVisualCache, payload) : payload;
      await db.update(
        'VisualCache',
        <String, Object?>{'accessed_at': DateTime.now().millisecondsSinceEpoch},
        where: 'cache_key = ?',
        whereArgs: <Object?>[cacheKey],
      );
      return bytes;
    }

    // Lazy migration from v7/older loose thumbnail/sample files.
    final File legacy = File(legacyPath);
    if (await legacy.exists()) {
      try {
        final Uint8List bytes = await legacy.readAsBytes();
        if (bytes.isNotEmpty) {
          await write(folder, legacyPath, bytes);
          await legacy.delete();
          return bytes;
        }
      } catch (_) {}
    }
    return null;
  }

  Future<void> write(String folder, String legacyPath, Uint8List bytes) async {
    if (bytes.isEmpty) return;
    final Database db = await _database();
    final Uint8List compressedBytes = await compute(_zlibCompressVisualCache, bytes);
    final bool useCompressed = compressedBytes.length < bytes.length;
    final Uint8List payload = useCompressed ? compressedBytes : bytes;
    final int now = DateTime.now().millisecondsSinceEpoch;
    await db.insert(
      'VisualCache',
      <String, Object?>{
        'cache_key': _key(folder, legacyPath),
        'folder': folder,
        'payload': payload,
        'compressed': useCompressed ? 1 : 0,
        'original_size': bytes.length,
        'stored_size': payload.length,
        'created_at': now,
        'accessed_at': now,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
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

    // Include legacy loose files until each one is lazily migrated.
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
print('CREATED compressed visual cache service')

policy = r'''import 'dart:convert';
import 'dart:io';

enum PortableDownloadFormat {
  original,
  jpeg,
  png;

  String get label => switch (this) {
        PortableDownloadFormat.original => 'Original',
        PortableDownloadFormat.jpeg => 'JPEG',
        PortableDownloadFormat.png => 'PNG',
      };

  String? get extension => switch (this) {
        PortableDownloadFormat.original => null,
        PortableDownloadFormat.jpeg => 'jpg',
        PortableDownloadFormat.png => 'png',
      };
}

class PortableMediaPolicy {
  PortableMediaPolicy._();

  static PortableDownloadFormat? _cachedFormat;

  static File get _file => File(
        '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data'
        '${Platform.pathSeparator}config${Platform.pathSeparator}portable_media_policy.json',
      );

  static Future<PortableDownloadFormat> getDownloadFormat() async {
    if (!Platform.isWindows) return PortableDownloadFormat.original;
    if (_cachedFormat != null) return _cachedFormat!;
    try {
      if (await _file.exists()) {
        final Object? decoded = jsonDecode(await _file.readAsString());
        if (decoded is Map) {
          final String value = decoded['downloadFormat']?.toString() ?? '';
          _cachedFormat = PortableDownloadFormat.values.firstWhere(
            (e) => e.name == value,
            orElse: () => PortableDownloadFormat.original,
          );
          return _cachedFormat!;
        }
      }
    } catch (_) {}
    _cachedFormat = PortableDownloadFormat.original;
    return _cachedFormat!;
  }

  static Future<void> setDownloadFormat(PortableDownloadFormat value) async {
    _cachedFormat = value;
    if (!Platform.isWindows) return;
    await _file.parent.create(recursive: true);
    await _file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(<String, Object?>{
        'downloadFormat': value.name,
      }),
      flush: true,
    );
  }
}
'''
Path('lib/src/services/portable_media_policy.dart').write_text(policy, encoding='utf-8')
print('CREATED portable media policy service')

# ---------------------------------------------------------------------------
# CustomNetworkImage: thumbnails/samples use packed DB cache on Windows.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    "import 'package:lolisnatcher/src/services/image_writer.dart';\n",
    "import 'package:lolisnatcher/src/services/compressed_visual_cache.dart';\nimport 'package:lolisnatcher/src/services/image_writer.dart';\n",
    'import-compressed-visual-cache',
)

replace_once(
    custom,
    """    final String tempFilePath = '$cacheFilePath.temp_${DateTime.now().microsecondsSinceEpoch}';

    File? cacheFile;

    // Check existing cache
    if (withCache) {
""",
    """    final String tempFilePath = '$cacheFilePath.temp_${DateTime.now().microsecondsSinceEpoch}';
    final bool useCompressedVisualCache =
        Platform.isWindows && withCache && CompressedVisualCache.isVisualFolder(cacheFolder);

    if (useCompressedVisualCache) {
      final Uint8List? packedBytes = await CompressedVisualCache.instance.read(
        cacheFolder!,
        cacheFilePath,
      );
      if (packedBytes != null && packedBytes.isNotEmpty) {
        chunkEvents?.add(
          ImageChunkEvent(
            cumulativeBytesLoaded: packedBytes.length,
            expectedTotalBytes: packedBytes.length,
          ),
        );
        onReceiveProgress?.call(packedBytes.length, packedBytes.length);
        onCacheDetected?.call(true);
        return packedBytes;
      }
      onCacheDetected?.call(false);
    }

    File? cacheFile;

    // Check existing loose-file cache (non-packed cache types only).
    if (withCache && !useCompressedVisualCache) {
""",
    'read-packed-visual-cache',
)

replace_once(
    custom,
    """    if (onCacheDetected != null) {
      onCacheDetected(cacheFile != null);
    }
""",
    """    if (onCacheDetected != null && !useCompressedVisualCache) {
      onCacheDetected(cacheFile != null);
    }
""",
    'avoid-overwriting-packed-cache-detection',
)

replace_once(
    custom,
    """      response = withCache
          ? await client.downloadUri(
""",
    """      response = withCache && !useCompressedVisualCache
          ? await client.downloadUri(
""",
    'packed-cache-download-to-memory',
)

replace_once(
    custom,
    """    if (withCache) {
      final tempFile = File(tempFilePath);
""",
    """    if (useCompressedVisualCache) {
      final Object? raw = response.data;
      final Uint8List bytes = raw is Uint8List
          ? raw
          : Uint8List.fromList((raw as List).cast<int>());
      final int? headerLen = int.tryParse(
        response.headers.value(HttpHeaders.contentLengthHeader) ?? '',
      );
      if (headerLen != null && headerLen > 0 && bytes.length != headerLen) {
        throw Exception('Download incomplete: Expected $headerLen bytes, got ${bytes.length}');
      }
      await CompressedVisualCache.instance.write(cacheFolder!, cacheFilePath, bytes);
      return bytes;
    }

    if (withCache) {
      final tempFile = File(tempFilePath);
""",
    'write-packed-visual-cache',
)

replace_once(
    custom,
    """    final File cacheFile = File(cacheFilePath);
    try {
""",
    """    if (Platform.isWindows && CompressedVisualCache.isVisualFolder(cacheFolder)) {
      await CompressedVisualCache.instance.delete(cacheFolder!, cacheFilePath);
      return;
    }

    final File cacheFile = File(cacheFilePath);
    try {
""",
    'delete-packed-visual-cache-entry',
)

# ---------------------------------------------------------------------------
# Image viewer: full-res may be displayed, but never persisted into media cache.
# Samples continue to use cache and therefore land in visual_cache.db.
# ---------------------------------------------------------------------------
viewer = 'lib/src/widgets/image/image_viewer.dart'
replace_count(
    viewer,
    '            withCache: settingsHandler.mediaCache,\n            cacheFolder: imageFolder,',
    "            withCache: settingsHandler.mediaCache && imageFolder != 'media',\n            cacheFolder: imageFolder,",
    2,
    'full-res-memory-only',
)

# ---------------------------------------------------------------------------
# ImageWriter: selected Windows download format + DB cache maintenance.
# ---------------------------------------------------------------------------
writer = 'lib/src/services/image_writer.dart'
replace_once(
    writer,
    "import 'package:dio/dio.dart';\n",
    "import 'package:dio/dio.dart';\nimport 'package:image/image.dart' as img;\n",
    'import-image-codec',
)
replace_once(
    writer,
    "import 'package:lolisnatcher/src/services/saf_file_cache.dart';\n",
    "import 'package:lolisnatcher/src/services/compressed_visual_cache.dart';\nimport 'package:lolisnatcher/src/services/portable_media_policy.dart';\nimport 'package:lolisnatcher/src/services/saf_file_cache.dart';\n",
    'import-v8-services',
)

replace_once(
    writer,
    """    final String fileName = getFilename(item, booru);
    await setPaths();

    // Don't do anything if file already exists
    final File image = File(path + fileName);
""",
    """    final String sourceFileName = getFilename(item, booru);
    final PortableDownloadFormat requestedFormat = Platform.isWindows
        ? await PortableMediaPolicy.getDownloadFormat()
        : PortableDownloadFormat.original;
    final String sourceExt = (item.fileExt ?? '').toLowerCase();
    final bool canConvertStaticImage = Platform.isWindows &&
        requestedFormat != PortableDownloadFormat.original &&
        item.mediaType.value.isImage &&
        sourceExt != 'avif';
    final String fileName = canConvertStaticImage
        ? _replaceFileExtension(sourceFileName, requestedFormat.extension!)
        : sourceFileName;
    await setPaths();

    // Don't do anything if the requested output file already exists.
    final File image = File(path + fileName);
""",
    'select-download-output-format',
)

replace_once(
    writer,
    """    if (!ignoreExists && (fileExists || item.isSnatched.value == true)) {
""",
    """    if (!ignoreExists && (fileExists || (item.isSnatched.value == true && !canConvertStaticImage))) {
""",
    'allow-redownload-in-new-output-format',
)

replace_once(
    writer,
    """      } else {
        await DioNetwork.download(
          url,
          '$path/$fileName',
          options: Options(
            responseType: ResponseType.bytes,
            contentType: '*/*',
          ),
          headers: headers,
          onReceiveProgress: onProgress,
          cancelToken: cancelToken,
        );
      }

      try {
""",
    """      } else if (canConvertStaticImage) {
        final String tempSourcePath =
            '$path/.lolisnatcher_source_${DateTime.now().microsecondsSinceEpoch}.tmp';
        try {
          await DioNetwork.download(
            url,
            tempSourcePath,
            options: Options(
              responseType: ResponseType.bytes,
              contentType: '*/*',
            ),
            headers: headers,
            onReceiveProgress: onProgress,
            cancelToken: cancelToken,
          );
          final Uint8List sourceBytes = await File(tempSourcePath).readAsBytes();
          final img.Image? decoded = img.decodeImage(sourceBytes);
          if (decoded == null) {
            throw FormatException('Could not decode image for ${requestedFormat.label} conversion');
          }
          final List<int> outputBytes = switch (requestedFormat) {
            PortableDownloadFormat.jpeg => img.encodeJpg(decoded, quality: 92),
            PortableDownloadFormat.png => img.encodePng(decoded),
            PortableDownloadFormat.original => sourceBytes,
          };
          await File('$path/$fileName').writeAsBytes(outputBytes, flush: true);
        } finally {
          final File tempSource = File(tempSourcePath);
          if (await tempSource.exists()) {
            try {
              await tempSource.delete();
            } catch (_) {}
          }
        }
      } else {
        await DioNetwork.download(
          url,
          '$path/$fileName',
          options: Options(
            responseType: ResponseType.bytes,
            contentType: '*/*',
          ),
          headers: headers,
          onReceiveProgress: onProgress,
          cancelToken: cancelToken,
        );
      }

      try {
""",
    'convert-static-download-on-materialization',
)

# Insert a filename helper before getFilename.
replace_once(
    writer,
    """  String getFilename(
""",
    """  String _replaceFileExtension(String fileName, String extension) {
    final int slash = fileName.lastIndexOf('/');
    final int dot = fileName.lastIndexOf('.');
    if (dot <= slash) return '$fileName.$extension';
    return '${fileName.substring(0, dot)}.$extension';
  }

  String getFilename(
""",
    'download-extension-helper',
)

replace_once(
    writer,
    """  Future deleteCacheFolder(String typeFolder) async {
    try {
      await setPaths();
""",
    """  Future deleteCacheFolder(String typeFolder) async {
    try {
      await setPaths();
      if (Platform.isWindows && CompressedVisualCache.isVisualFolder(typeFolder)) {
        await CompressedVisualCache.instance.clearFolder(typeFolder);
        return true;
      }
""",
    'clear-packed-cache-folder',
)

replace_once(
    writer,
    """  Future<Map<String, int>> getCacheStat(String? typeFolder) async {
    String cacheDirPath;
""",
    """  Future<Map<String, int>> getCacheStat(String? typeFolder) async {
    if (Platform.isWindows && CompressedVisualCache.isVisualFolder(typeFolder)) {
      return CompressedVisualCache.instance.getStats(typeFolder!);
    }
    String cacheDirPath;
""",
    'packed-cache-stats',
)

replace_once(
    writer,
    """        ),
      );
    } catch (e) {
      print('Image Writer Exception :: cleanupCache :: $e');
""",
    """        ),
      );
      if (Platform.isWindows) {
        await CompressedVisualCache.instance.cleanup(
          maxAge: settingsHandler.cacheDuration,
          maxBytes: (settingsHandler.cacheSize * pow(1024, 3)).toInt(),
        );
      }
    } catch (e) {
      print('Image Writer Exception :: cleanupCache :: $e');
""",
    'cleanup-packed-cache',
)

# ---------------------------------------------------------------------------
# Save/cache settings UI: format selector and accurate DB entry stats.
# ---------------------------------------------------------------------------
settings_page = 'lib/src/pages/settings/save_cache_page.dart'
replace_once(
    settings_page,
    "import 'package:lolisnatcher/src/services/image_writer.dart';\n",
    "import 'package:lolisnatcher/src/services/compressed_visual_cache.dart';\nimport 'package:lolisnatcher/src/services/image_writer.dart';\nimport 'package:lolisnatcher/src/services/portable_media_policy.dart';\n",
    'import-v8-cache-settings-services',
)

replace_once(
    settings_page,
    """  late ImageQuality snatchMode;
  bool jsonWrite = false,
""",
    """  late ImageQuality snatchMode;
  PortableDownloadFormat downloadFormat = PortableDownloadFormat.original;
  bool jsonWrite = false,
""",
    'download-format-state',
)

replace_once(
    settings_page,
    """    favouriteOnSnatch = settingsHandler.favouriteOnSnatch;

    getCacheStats(null);
""",
    """    favouriteOnSnatch = settingsHandler.favouriteOnSnatch;

    unawaited(_loadPortableDownloadFormat());
    getCacheStats(null);
""",
    'load-portable-download-format',
)

replace_once(
    settings_page,
    """  Future<void> getCacheStats(String? folder) async {
""",
    """  Future<void> _loadPortableDownloadFormat() async {
    final PortableDownloadFormat value = await PortableMediaPolicy.getDownloadFormat();
    if (!mounted) return;
    setState(() {
      downloadFormat = value;
    });
  }

  Future<void> getCacheStats(String? folder) async {
""",
    'portable-format-loader-method',
)

replace_once(
    settings_page,
    """    for (final _CacheType type in cacheTypesToGet) {
      final ReceivePort receivePort = ReceivePort();
""",
    """    for (final _CacheType type in cacheTypesToGet) {
      if (Platform.isWindows && CompressedVisualCache.isVisualFolder(type.folder)) {
        final Map<String, int> stat = await CompressedVisualCache.instance.getStats(type.folder!);
        cacheStats.add(<String, dynamic>{'type': type.folder, ...stat});
        if (mounted) setState(() {});
        continue;
      }
      final ReceivePort receivePort = ReceivePort();
""",
    'packed-cache-settings-stats',
)

replace_once(
    settings_page,
    """              SettingsTextInput(
                controller: snatchCooldownController,
""",
    """              if (Platform.isWindows)
                SettingsOptionsList<PortableDownloadFormat>(
                  value: downloadFormat,
                  items: PortableDownloadFormat.values,
                  onChanged: (PortableDownloadFormat? newValue) {
                    final PortableDownloadFormat value =
                        newValue ?? PortableDownloadFormat.original;
                    setState(() {
                      downloadFormat = value;
                    });
                    unawaited(PortableMediaPolicy.setDownloadFormat(value));
                  },
                  title: 'Formato de descarga (Windows)',
                  itemTitleBuilder: (e) => e?.label ?? '',
                ),
              SettingsTextInput(
                controller: snatchCooldownController,
""",
    'windows-download-format-selector',
)

replace_once(
    settings_page,
    """              SettingsToggle(
                value: thumbnailCache,
""",
    r"""              if (Platform.isWindows)
                const SettingsButton(
                  name: r'Cache visual comprimida: Data\cache\visual_cache.db',
                  enabled: false,
                ),
              SettingsToggle(
                value: thumbnailCache,
""",
    'compressed-cache-ui-note',
)

# Guards
checks = {
    'compressed cache service': Path('lib/src/services/compressed_visual_cache.dart').exists(),
    'portable media policy': Path('lib/src/services/portable_media_policy.dart').exists(),
    'db cache read': 'useCompressedVisualCache' in Path(custom).read_text(encoding='utf-8'),
    'fullres memory only': "settingsHandler.mediaCache && imageFolder != 'media'" in Path(viewer).read_text(encoding='utf-8'),
    'format conversion': 'img.encodeJpg' in Path(writer).read_text(encoding='utf-8'),
    'png conversion': 'img.encodePng' in Path(writer).read_text(encoding='utf-8'),
    'format selector': 'Formato de descarga (Windows)' in Path(settings_page).read_text(encoding='utf-8'),
    'db cache path note': 'visual_cache.db' in Path(settings_page).read_text(encoding='utf-8'),
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8 guard failed: {label}')

print('V8_COMPRESSED_VISUAL_CACHE_DB=PASS')
print('V8_THUMBNAILS_SAMPLES_PACKED=PASS')
print('V8_FULLRES_MEMORY_ONLY=PASS')
print('V8_DOWNLOAD_FORMAT_SELECTOR=PASS')
print('V8_PATCH=PASS')
