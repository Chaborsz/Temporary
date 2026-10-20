from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.15 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.15 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) Every Thumbnail on Windows is thumbnailURL-only. Samples belong to the
#    actual viewer provider and are memory-only there; Thumbnail must never ask
#    for sampleURL, including viewer placeholders.
# ---------------------------------------------------------------------------
thumbnail = 'lib/src/widgets/thumbnail/thumbnail.dart'
replace_once(
    thumbnail,
    "if (Platform.isWindows && widget.isStandalone) {",
    "if (Platform.isWindows) {",
    'all-windows-thumbnail-widgets-thumbnail-only',
)


# ---------------------------------------------------------------------------
# 2) CustomNetworkImage must never construct a physical thumbnails/samples path
#    on Windows. The packed cache gets an opaque logical key preserving the same
#    basename that the existing DB key function expects.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    """    final Uri resolved = Uri.base.resolve(url);
    final String cacheFilePath = await ImageWriter().getCachePathString(
      resolved.toString(),
      cacheFolder ?? 'media',
      clearName: cacheFolder != 'favicons',
      fileNameExtras: fileNameExtras,
    );

    final String tempFilePath = '$cacheFilePath.temp_${DateTime.now().microsecondsSinceEpoch}';
    final bool useCompressedVisualCache =
        Platform.isWindows && withCache && CompressedVisualCache.isVisualFolder(cacheFolder);
""",
    """    final Uri resolved = Uri.base.resolve(url);
    final bool useCompressedVisualCache =
        Platform.isWindows && withCache && CompressedVisualCache.isVisualFolder(cacheFolder);

    final String cacheFilePath;
    if (useCompressedVisualCache) {
      final ImageWriter keyWriter = ImageWriter();
      final String logicalName = keyWriter.sanitizeName(
        keyWriter.parseThumbUrlToName(resolved.toString()),
        fileNameExtras: fileNameExtras,
      );
      cacheFilePath =
          '__packed_visual__${Platform.pathSeparator}${cacheFolder!}${Platform.pathSeparator}$logicalName';
    } else {
      cacheFilePath = await ImageWriter().getCachePathString(
        resolved.toString(),
        cacheFolder ?? 'media',
        clearName: cacheFolder != 'favicons',
        fileNameExtras: fileNameExtras,
      );
    }

    final String tempFilePath = '$cacheFilePath.temp_${DateTime.now().microsecondsSinceEpoch}';
""",
    'packed-read-write-never-builds-loose-path',
)

replace_once(
    custom,
    """    final Uri resolved = Uri.base.resolve(url);
    final String cacheFilePath = await ImageWriter().getCachePathString(
      resolved.toString(),
      cacheFolder ?? 'media',
      clearName: cacheFolder != 'favicons',
      fileNameExtras: fileNameExtras,
    );
    if (Platform.isWindows && CompressedVisualCache.isVisualFolder(cacheFolder)) {
      await CompressedVisualCache.instance.delete(cacheFolder!, cacheFilePath);
      return;
    }
""",
    """    final Uri resolved = Uri.base.resolve(url);
    if (Platform.isWindows && CompressedVisualCache.isVisualFolder(cacheFolder)) {
      final ImageWriter keyWriter = ImageWriter();
      final String logicalName = keyWriter.sanitizeName(
        keyWriter.parseThumbUrlToName(resolved.toString()),
        fileNameExtras: fileNameExtras,
      );
      final String logicalPath =
          '__packed_visual__${Platform.pathSeparator}${cacheFolder!}${Platform.pathSeparator}$logicalName';
      await CompressedVisualCache.instance.delete(cacheFolder!, logicalPath);
      return;
    }

    final String cacheFilePath = await ImageWriter().getCachePathString(
      resolved.toString(),
      cacheFolder ?? 'media',
      clearName: cacheFolder != 'favicons',
      fileNameExtras: fileNameExtras,
    );
""",
    'packed-delete-never-builds-loose-path',
)


# ---------------------------------------------------------------------------
# 3) Hard API-level block: any remaining code path asking ImageWriter for a
#    physical visual-cache path on Windows is a bug. Returning/creating such a
#    path is forbidden. Existing getCachePath/writeCacheFromBytes blocks from
#    v8.12 remain in force; this closes getCachePathString as well.
# ---------------------------------------------------------------------------
image_writer = 'lib/src/services/image_writer.dart'
replace_once(
    image_writer,
    """  Future<String> getCachePathString(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    await setPaths();
""",
    """  Future<String> getCachePathString(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {
      throw StateError('Loose visual cache paths are forbidden on Windows');
    }

    await setPaths();
""",
    'forbid-loose-visual-cache-path-api',
)

replace_once(
    image_writer,
    """  Future deleteFileFromCache(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
  }) async {
    try {
""",
    """  Future deleteFileFromCache(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
  }) async {
    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {
      return null;
    }

    try {
""",
    'block-loose-visual-delete-path-api',
)


# ---------------------------------------------------------------------------
# 4) Defense in depth: if a stale/foreign build recreates either loose folder
#    while this process is running, packed cache operations purge it at most once
#    every 5 seconds. This is not the primary mechanism; the hard path blocks
#    above prevent this build from creating them in the first place.
# ---------------------------------------------------------------------------
cache = 'lib/src/services/compressed_visual_cache.dart'
replace_once(
    cache,
    """  Future<Database>? _databaseFuture;

  static bool isVisualFolder(String? folder) => folder == 'thumbnails' || folder == 'samples';
""",
    """  Future<Database>? _databaseFuture;
  int _lastLoosePurgeMs = 0;

  static bool isVisualFolder(String? folder) => folder == 'thumbnails' || folder == 'samples';

  Future<void> _purgeForbiddenLooseVisualFolders({bool force = false}) async {
    final int now = DateTime.now().millisecondsSinceEpoch;
    if (!force && now - _lastLoosePurgeMs < 5000) return;
    _lastLoosePurgeMs = now;

    for (final String folder in const <String>['thumbnails', 'samples']) {
      final Directory legacyDir = Directory('${await _rootPath()}$folder');
      if (!await legacyDir.exists()) continue;
      try {
        await legacyDir.delete(recursive: true);
      } catch (_) {}
    }
  }
""",
    'throttled-loose-visual-purge-helper',
)

replace_once(
    cache,
    """    // DB-only invariant for Windows portable visual cache. Old/regressed loose
    // files are expendable cache data and can always be re-fetched.
    for (final String folder in const <String>['thumbnails', 'samples']) {
      final Directory legacyDir = Directory('${await _rootPath()}$folder');
      if (await legacyDir.exists()) {
        try {
          await legacyDir.delete(recursive: true);
        } catch (_) {}
      }
    }

    return db;
""",
    """    // DB-only invariant for Windows portable visual cache.
    await _purgeForbiddenLooseVisualFolders(force: true);

    return db;
""",
    'db-open-uses-central-loose-purge',
)

replace_once(
    cache,
    """  Future<Uint8List?> read(String folder, String legacyPath) async {
    final Database db = await _database();
""",
    """  Future<Uint8List?> read(String folder, String legacyPath) async {
    await _purgeForbiddenLooseVisualFolders();
    final Database db = await _database();
""",
    'packed-read-throttled-loose-purge',
)

replace_once(
    cache,
    """  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    if (bytes.isEmpty) return bytes;
""",
    """  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    await _purgeForbiddenLooseVisualFolders();
    if (bytes.isEmpty) return bytes;
""",
    'packed-write-throttled-loose-purge',
)


# Guards.
thumb_final = Path(thumbnail).read_text(encoding='utf-8')
custom_final = Path(custom).read_text(encoding='utf-8')
writer_final = Path(image_writer).read_text(encoding='utf-8')
cache_final = Path(cache).read_text(encoding='utf-8')
checks = {
    'all Windows thumbnails are thumbnail-only': 'if (Platform.isWindows) {' in thumb_final and 'if (Platform.isWindows && widget.isStandalone) {' not in thumb_final,
    'packed custom path is opaque': custom_final.count('__packed_visual__') >= 2,
    'packed visual path bypasses getCachePathString': 'if (useCompressedVisualCache) {' in custom_final,
    'physical visual path API forbidden': "throw StateError('Loose visual cache paths are forbidden on Windows');" in writer_final,
    'main writer visual guard retained': "typeFolder == 'thumbnails' || typeFolder == 'samples'" in writer_final,
    'central purge helper exists': '_purgeForbiddenLooseVisualFolders' in cache_final,
    'purge runs on read': 'Future<Uint8List?> read(String folder, String legacyPath) async {\n    await _purgeForbiddenLooseVisualFolders();' in cache_final,
    'purge runs on write': 'Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {\n    await _purgeForbiddenLooseVisualFolders();' in cache_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.15 guard failed: {label}')

print('V8_15_ALL_WINDOWS_THUMBNAILS_THUMBNAIL_ONLY=PASS')
print('V8_15_PACKED_VISUAL_LOGICAL_KEYS=PASS')
print('V8_15_LOOSE_VISUAL_PATH_API_FORBIDDEN=PASS')
print('V8_15_THROTTLED_LOOSE_VISUAL_PURGE=PASS')
print('V8_15_STRICT_DB_ONLY_VISUAL_CACHE=PASS')
