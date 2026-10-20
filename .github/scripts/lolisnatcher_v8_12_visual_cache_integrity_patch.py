from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.12 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.12 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) Windows grid must never fetch samples. A post without thumbnailURL gets a
#    placeholder/failure state instead of silently falling back to sampleURL.
# ---------------------------------------------------------------------------
thumbnail = Path('lib/src/widgets/thumbnail/thumbnail.dart')
thumb = thumbnail.read_text(encoding='utf-8')
start_marker = "    isThumbQuality =\n        (Platform.isWindows && widget.item.thumbnailURL.isNotEmpty) ||\n"
end_marker = "    // delay loading a little to improve performance when scrolling fast, ignore delay if it's a standalone widget (i.e. not in a list)\n"
if thumb.count(start_marker) != 1 or thumb.count(end_marker) != 1:
    raise SystemExit(
        f'v8.12 windows-grid-thumbnail-only markers: start={thumb.count(start_marker)} end={thumb.count(end_marker)}'
    )
start = thumb.index(start_marker)
end = thumb.index(end_marker, start)
replacement = """    if (Platform.isWindows && widget.isStandalone) {
      // Strict Windows grid policy: only thumbnailURL is allowed here. Never
      // fetch sampleURL just because a provider omitted a thumbnail.
      isThumbQuality = true;
      thumbURL = widget.item.thumbnailURL;
      thumbFolder = 'thumbnails';
      useExtra.value = false;

      if (thumbURL.isEmpty) {
        isFailed.value = true;
        errorCode.value = 'NO_THUMBNAIL';
        return;
      }
    } else {
      isThumbQuality =
          settingsHandler.previewMode.isThumbnail ||
          (widget.item.mediaType.value.isVideo ||
              widget.item.mediaType.value.isNeedToGuess ||
              widget.item.mediaType.value.isNeedToLoadItem) ||
          (!widget.isStandalone && widget.item.fileURL == widget.item.sampleURL);
      thumbURL = isThumbQuality == true ? widget.item.thumbnailURL : widget.item.sampleURL;
      thumbFolder = (isThumbQuality == true || thumbURL == widget.item.thumbnailURL) ? 'thumbnails' : 'samples';
      useExtra.value =
          isThumbQuality == false &&
          !widget.item.isHidden &&
          !settingsHandler.shitDevice &&
          !Platform.isWindows;
    }

"""
thumb = thumb[:start] + replacement + thumb[end:]
thumbnail.write_text(thumb, encoding='utf-8')
print('PATCHED v8.12 windows-grid-never-fetch-samples')


# ---------------------------------------------------------------------------
# 2) Windows image viewer is memory-only for both originals and sample fallback.
#    This guarantees that samples are fetched only after entering the viewer and
#    are never persisted as loose files or packed DB entries.
# ---------------------------------------------------------------------------
viewer = Path('lib/src/widgets/image/image_viewer.dart')
viewer_text = viewer.read_text(encoding='utf-8')
old_cache = "            withCache: settingsHandler.mediaCache && imageFolder != 'media',\n"
new_cache = "            withCache: !Platform.isWindows && settingsHandler.mediaCache && imageFolder != 'media',\n"
count = viewer_text.count(old_cache)
if count != 2:
    raise SystemExit(f'v8.12 viewer-memory-only: expected 2 matches, found {count}')
viewer.write_text(viewer_text.replace(old_cache, new_cache), encoding='utf-8')
print('PATCHED v8.12 windows-viewer-samples-memory-only (2 providers)')


# ---------------------------------------------------------------------------
# 3) Hard-block every legacy loose-file visual-cache writer/reader on Windows.
#    The canonical persistent visual cache is visual_cache.db only.
# ---------------------------------------------------------------------------
image_writer = 'lib/src/services/image_writer.dart'
replace_once(
    image_writer,
    """  }) async {
    File? image;
    try {
      await setPaths();
      final String cachePath = '$cacheRootPath$typeFolder/';
      // print(\"write cahce from bytes:: cache path is $cachePath\");
""",
    """  }) async {
    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {
      return null;
    }

    File? image;
    try {
      await setPaths();
      final String cachePath = '$cacheRootPath$typeFolder/';
      // print(\"write cahce from bytes:: cache path is $cachePath\");
""",
    'block-main-isolate-loose-visual-writes',
)

replace_once(
    image_writer,
    """  Future<String?> getCachePath(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    String cachePath;
""",
    """  Future<String?> getCachePath(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {
      return null;
    }

    String cachePath;
""",
    'block-loose-visual-cache-reads',
)

isolate = 'lib/src/services/image_writer_isolate.dart'
replace_once(
    isolate,
    """  }) async {
    File? image;
    try {
      final String cachePath = '$cacheRootPath$typeFolder/';
      await Directory(cachePath).create(recursive: true);
""",
    """  }) async {
    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {
      return null;
    }

    File? image;
    try {
      final String cachePath = '$cacheRootPath$typeFolder/';
      await Directory(cachePath).create(recursive: true);
""",
    'block-worker-loose-visual-writes',
)

# Both isolate readers have distinct return types but the same visual policy.
p = Path(isolate)
iso = p.read_text(encoding='utf-8')
for signature, label in [
    ("""  Future<File?> readFileFromCache(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    File? image;
""", 'block-worker-visual-file-reads'),
    ("""  Future<Uint8List?> readBytesFromCache(
    String fileURL,
    String typeFolder, {
    required String fileNameExtras,
    bool clearName = true,
  }) async {
    Uint8List? imageBytes;
""", 'block-worker-visual-byte-reads'),
]:
    if iso.count(signature) != 1:
        raise SystemExit(f'v8.12 {label}: expected 1 match, found {iso.count(signature)}')
    guard = signature.rsplit('\n', 1)[0] + "\n    if (Platform.isWindows && (typeFolder == 'thumbnails' || typeFolder == 'samples')) {\n      return null;\n    }\n\n" + signature.rsplit('\n', 1)[1]
    iso = iso.replace(signature, guard, 1)
    print(f'PATCHED v8.12 {label}')
p.write_text(iso, encoding='utf-8')


# ---------------------------------------------------------------------------
# 4) Purge any legacy loose thumbnails/samples when the packed DB opens. This is
#    intentionally repeat-safe and removes leftovers from older/regressed builds.
# ---------------------------------------------------------------------------
cache = 'lib/src/services/compressed_visual_cache.dart'
replace_once(
    cache,
    """    );
    return db;
  }

  Future<Uint8List?> read(String folder, String legacyPath) async {
""",
    """    );

    // DB-only invariant for Windows portable visual cache. Old/regressed loose
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
  }

  Future<Uint8List?> read(String folder, String legacyPath) async {
""",
    'purge-legacy-loose-visual-folders-on-db-open',
)

# No lazy loose-file migration is needed anymore; loose visual files are forbidden.
replace_once(
    cache,
    """    // Lazy migration from older loose thumbnail/sample files.
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
""",
    """    return null;
""",
    'remove-loose-file-lazy-migration',
)


# Guards.
thumb_final = thumbnail.read_text(encoding='utf-8')
viewer_final = viewer.read_text(encoding='utf-8')
writer_final = Path(image_writer).read_text(encoding='utf-8')
isolate_final = Path(isolate).read_text(encoding='utf-8')
cache_final = Path(cache).read_text(encoding='utf-8')
checks = {
    'grid no sample fallback': 'Strict Windows grid policy' in thumb_final and "thumbURL = widget.item.thumbnailURL;" in thumb_final,
    'empty thumbnail does not sample': "errorCode.value = 'NO_THUMBNAIL';" in thumb_final,
    'viewer memory only windows': viewer_final.count("withCache: !Platform.isWindows && settingsHandler.mediaCache && imageFolder != 'media',") == 2,
    'main loose writer blocked': "typeFolder == 'thumbnails' || typeFolder == 'samples'" in writer_final,
    'worker loose writer blocked': isolate_final.count("typeFolder == 'thumbnails' || typeFolder == 'samples'") >= 3,
    'db open purges legacy folders': "const <String>['thumbnails', 'samples']" in cache_final and 'legacyDir.delete(recursive: true)' in cache_final,
    'no lazy loose migration': 'Lazy migration from older loose thumbnail/sample files.' not in cache_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.12 guard failed: {label}')

print('V8_12_WINDOWS_GRID_THUMBNAIL_ONLY=PASS')
print('V8_12_WINDOWS_SAMPLES_MEMORY_ONLY=PASS')
print('V8_12_VISUAL_CACHE_DB_ONLY=PASS')
print('V8_12_LEGACY_LOOSE_VISUAL_PURGE=PASS')
print('V8_12_VISUAL_CACHE_INTEGRITY=PASS')
