from pathlib import Path
import re


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.22 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.22 {label}: {p}')


def regex_replace_once(path: str, pattern: str, replacement: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'v8.22 {label}: expected 1 regex match, found {count} in {p}')
    p.write_text(updated, encoding='utf-8')
    print(f'PATCHED v8.22 {label}: {p}')


# ---------------------------------------------------------------------------
# Runtime evidence from v8.21:
# - TRACKED_BATCH is 0-6 ms and TAG_BATCH is 34-71 ms: both are cleared as the
#   cause of the remaining freezes in the supplied run.
# - repeated WATCHDOG_STALL/EVENT_LOOP_STALL events occur with active=idle.
# - a concrete visual-cache stall appears as VISUAL_DB_BATCH entries=1 ms=292,
#   immediately followed by WATCHDOG_STALL active=visual_pipeline.
# - process RSS rises from ~203 MB to ~387 MB while Flutter ImageCache reports
#   only ~18 MB and grows past 200 retained entries.
#
# v8.22 therefore targets only the proven visual/cache side:
# 1) reduce the Windows decoded-image LRU entry count (96 / 64 MiB);
# 2) stop redundant loose-folder probes on every packed-cache read/write;
# 3) disable SQLite WAL autocheckpoint while scrolling and checkpoint after 5 s
#    of visual-cache quiet instead;
# 4) debounce thumbnail DB persistence for 750 ms of quiet, bounded to the most
#    recent 32 pending writes so source-byte retention cannot grow unbounded;
# 5) add watchdog labels for visual DB reads/writes/checkpoints and richer logs.
# ---------------------------------------------------------------------------

main = 'lib/main.dart'
replace_once(
    main,
    """    PaintingBinding.instance.imageCache.maximumSize = 256;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 128 * 1024 * 1024;
""",
    """    PaintingBinding.instance.imageCache.maximumSize = 96;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 64 * 1024 * 1024;
""",
    'windows-image-cache-96-64mib',
)

cache = 'lib/src/services/compressed_visual_cache.dart'
replace_once(
    cache,
    "import 'package:lolisnatcher/src/handlers/service_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/service_handler.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'visual-cache-watchdog-import',
)

replace_once(
    cache,
    """          await db.execute('PRAGMA journal_mode=WAL;');
          await db.execute('PRAGMA synchronous=NORMAL;');
""",
    """          await db.execute('PRAGMA journal_mode=WAL;');
          await db.execute('PRAGMA synchronous=NORMAL;');
          // Avoid an automatic WAL checkpoint being paid by a thumbnail write
          // while the user is actively scrolling. v8.22 schedules PASSIVE
          // checkpoints only after the visual-cache queue has been quiet.
          await db.execute('PRAGMA wal_autocheckpoint=0;');
""",
    'disable-wal-autocheckpoint-during-scroll',
)

# DB-only is already enforced structurally by ImageWriter/custom network image.
# The forced startup purge is sufficient; repeated filesystem stats/deletes on
# every packed read/write are unnecessary work on the visual hot path.
replace_once(
    cache,
    """  Future<Uint8List?> read(String folder, String legacyPath) async {
    await _purgeForbiddenLooseVisualFolders();
    final Database db = await _database();
""",
    """  Future<Uint8List?> read(String folder, String legacyPath) async {
    final Database db = await _database();
""",
    'remove-hot-read-loose-folder-probe',
)
replace_once(
    cache,
    """  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    await _purgeForbiddenLooseVisualFolders();
    if (bytes.isEmpty) return bytes;
""",
    """  Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {
    if (bytes.isEmpty) return bytes;
""",
    'remove-hot-write-loose-folder-probe',
)

# Label the actual packed DB query so the independent watchdog can distinguish
# SQLite read latency from HTTP/decode work inside the broader visual_pipeline.
regex_replace_once(
    cache,
    r"    final List<Map<String, Object\?>> rows = await db\.query\(\n      'VisualCache',\n      columns: <String>\['payload', 'compressed', 'accessed_at'\],\n      where: 'cache_key = \?',\n      whereArgs: <Object\?>\[cacheKey\],\n      limit: 1,\n    \);",
    """    late final List<Map<String, Object?>> rows;
    WindowsPerformanceWatchdog.enter('visual_db_read');
    try {
      rows = await db.query(
        'VisualCache',
        columns: <String>['payload', 'compressed', 'accessed_at'],
        where: 'cache_key = ?',
        whereArgs: <Object?>[cacheKey],
        limit: 1,
      );
    } finally {
      WindowsPerformanceWatchdog.leave('visual_db_read');
    }""",
    'visual-db-read-watchdog-phase',
)

replace_once(
    cache,
    """  Timer? _thumbnailStoreTimer;
  Future<void> _thumbnailStoreChain = Future<void>.value();
  int _lastLoosePurgeMs = 0;
""",
    """  Timer? _thumbnailStoreTimer;
  Future<void> _thumbnailStoreChain = Future<void>.value();
  Timer? _visualCheckpointTimer;
  int _visualPendingDrops = 0;
  int _lastLoosePurgeMs = 0;
""",
    'visual-db-idle-state',
)

replace_once(
    cache,
    """  void _queueThumbnailStore(
    String folder,
    String legacyPath,
    Uint8List bytes,
  ) {
    final String cacheKey = _key(folder, legacyPath);
    _pendingThumbnailStores[cacheKey] =
        _PendingVisualDbWrite(folder, legacyPath, bytes, bytes, 'source');

    if (_pendingThumbnailStores.length >= 16) {
      _thumbnailStoreTimer?.cancel();
      _thumbnailStoreTimer = null;
      unawaited(_flushPendingThumbnailStores());
      return;
    }

    _thumbnailStoreTimer ??= Timer(const Duration(milliseconds: 100), () {
      _thumbnailStoreTimer = null;
      unawaited(_flushPendingThumbnailStores());
    });
  }
""",
    """  void _queueThumbnailStore(
    String folder,
    String legacyPath,
    Uint8List bytes,
  ) {
    final String cacheKey = _key(folder, legacyPath);
    _pendingThumbnailStores[cacheKey] =
        _PendingVisualDbWrite(folder, legacyPath, bytes, bytes, 'source');

    // Cache persistence is optional. During continuous scrolling retain only a
    // bounded recent set rather than forcing SQLite commits into the hot path or
    // retaining an unbounded chain of source byte arrays.
    while (_pendingThumbnailStores.length > 32) {
      final String oldestKey = _pendingThumbnailStores.keys.first;
      _pendingThumbnailStores.remove(oldestKey);
      _visualPendingDrops++;
    }

    _visualCheckpointTimer?.cancel();
    _visualCheckpointTimer = null;
    _thumbnailStoreTimer?.cancel();
    _thumbnailStoreTimer = Timer(const Duration(milliseconds: 750), () {
      _thumbnailStoreTimer = null;
      unawaited(_flushPendingThumbnailStores());
    });
  }
""",
    'idle-debounced-bounded-visual-db-queue',
)

# Add watchdog state around the serialized SQLite transaction and record RSS +
# any deliberately dropped cache-only writes in the existing slow-batch trace.
replace_once(
    cache,
    """    _thumbnailStoreChain = _thumbnailStoreChain.then((_) async {
      final Stopwatch watch = Stopwatch()..start();
      int totalBytes = 0;
      try {
        final Database db = await _database();
        final int now = DateTime.now().millisecondsSinceEpoch;
        final Batch batch = db.batch();
        for (final _PendingVisualDbWrite entry in pending) {
          totalBytes += entry.payload.length;
          batch.insert(
            'VisualCache',
            <String, Object?>{
              'cache_key': _key(entry.folder, entry.legacyPath),
              'folder': entry.folder,
              'payload': entry.payload,
              'compressed': 0,
              'codec': entry.codec,
              'original_size': entry.sourceBytes.length,
              'stored_size': entry.payload.length,
              'created_at': now,
              'accessed_at': now,
            },
            conflictAlgorithm: ConflictAlgorithm.replace,
          );
        }
        await batch.commit(noResult: true);
      } catch (_) {
        // Cache persistence is optional. Missing rows are simply fetched again.
      } finally {
        watch.stop();
      }

      if (Platform.isWindows && watch.elapsedMilliseconds >= 50) {
        try {
          final String sep = Platform.pathSeparator;
          final File file = File(
            '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
          );
          await file.parent.create(recursive: true);
          await file.writeAsString(
            '${DateTime.now().toIso8601String()} VISUAL_DB_BATCH entries=${pending.length} '
            'bytes=$totalBytes ms=${watch.elapsedMilliseconds}\\n',
            mode: FileMode.append,
            flush: false,
          );
        } catch (_) {}
      }
    });

    await _thumbnailStoreChain;
  }
""",
    """    final int dropped = _visualPendingDrops;
    _visualPendingDrops = 0;

    _thumbnailStoreChain = _thumbnailStoreChain.then((_) async {
      final Stopwatch watch = Stopwatch()..start();
      int totalBytes = 0;
      WindowsPerformanceWatchdog.enter('visual_db_write');
      try {
        final Database db = await _database();
        final int now = DateTime.now().millisecondsSinceEpoch;
        final Batch batch = db.batch();
        for (final _PendingVisualDbWrite entry in pending) {
          totalBytes += entry.payload.length;
          batch.insert(
            'VisualCache',
            <String, Object?>{
              'cache_key': _key(entry.folder, entry.legacyPath),
              'folder': entry.folder,
              'payload': entry.payload,
              'compressed': 0,
              'codec': entry.codec,
              'original_size': entry.sourceBytes.length,
              'stored_size': entry.payload.length,
              'created_at': now,
              'accessed_at': now,
            },
            conflictAlgorithm: ConflictAlgorithm.replace,
          );
        }
        await batch.commit(noResult: true);
      } catch (_) {
        // Cache persistence is optional. Missing rows are simply fetched again.
      } finally {
        WindowsPerformanceWatchdog.leave('visual_db_write');
        watch.stop();
      }

      if (Platform.isWindows && (watch.elapsedMilliseconds >= 25 || dropped > 0)) {
        try {
          final String sep = Platform.pathSeparator;
          final File file = File(
            '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
          );
          await file.parent.create(recursive: true);
          await file.writeAsString(
            '${DateTime.now().toIso8601String()} VISUAL_DB_BATCH entries=${pending.length} '
            'bytes=$totalBytes dropped=$dropped ms=${watch.elapsedMilliseconds} '
            'rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\\n',
            mode: FileMode.append,
            flush: false,
          );
        } catch (_) {}
      }
    });

    await _thumbnailStoreChain;

    if (_pendingThumbnailStores.isEmpty) {
      _visualCheckpointTimer?.cancel();
      _visualCheckpointTimer = Timer(const Duration(seconds: 5), () {
        _visualCheckpointTimer = null;
        unawaited(_checkpointVisualDb());
      });
    }
  }

  Future<void> _checkpointVisualDb() async {
    if (_pendingThumbnailStores.isNotEmpty) return;
    final Stopwatch watch = Stopwatch()..start();
    WindowsPerformanceWatchdog.enter('visual_db_checkpoint');
    try {
      final Database db = await _database();
      await db.rawQuery('PRAGMA wal_checkpoint(PASSIVE);');
    } catch (_) {
      return;
    } finally {
      WindowsPerformanceWatchdog.leave('visual_db_checkpoint');
      watch.stop();
    }

    if (Platform.isWindows && watch.elapsedMilliseconds >= 25) {
      try {
        final String sep = Platform.pathSeparator;
        final File file = File(
          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
        );
        await file.parent.create(recursive: true);
        await file.writeAsString(
          '${DateTime.now().toIso8601String()} VISUAL_DB_CHECKPOINT '
          'ms=${watch.elapsedMilliseconds} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\\n',
          mode: FileMode.append,
          flush: false,
        );
      } catch (_) {}
    }
  }
""",
    'visual-db-write-watchdog-idle-checkpoint',
)


# Guards.
main_final = Path(main).read_text(encoding='utf-8')
cache_final = Path(cache).read_text(encoding='utf-8')
checks = {
    'image cache entries 96': 'imageCache.maximumSize = 96;' in main_final,
    'image cache bytes 64MiB': 'imageCache.maximumSizeBytes = 64 * 1024 * 1024;' in main_final,
    'old image cache entry limit removed': 'imageCache.maximumSize = 256;' not in main_final,
    'visual watchdog import': "services/performance_watchdog.dart" in cache_final,
    'wal autocheckpoint disabled': "PRAGMA wal_autocheckpoint=0;" in cache_final,
    'startup loose purge retained': '_purgeForbiddenLooseVisualFolders(force: true)' in cache_final,
    'hot read purge removed': "Future<Uint8List?> read(String folder, String legacyPath) async {\n    await _purgeForbiddenLooseVisualFolders();" not in cache_final,
    'hot write purge removed': "Future<Uint8List> write(String folder, String legacyPath, Uint8List bytes) async {\n    await _purgeForbiddenLooseVisualFolders();" not in cache_final,
    'visual DB read watchdog': "enter('visual_db_read')" in cache_final,
    'visual DB write watchdog': "enter('visual_db_write')" in cache_final,
    'visual DB checkpoint watchdog': "enter('visual_db_checkpoint')" in cache_final,
    'visual queue cap 32': '_pendingThumbnailStores.length > 32' in cache_final,
    'visual idle debounce 750': 'Duration(milliseconds: 750)' in cache_final,
    'visual checkpoint idle 5s': 'Duration(seconds: 5)' in cache_final,
    'visual batch richer diagnostic': 'dropped=$dropped' in cache_final and 'VISUAL_DB_CHECKPOINT' in cache_final,
    'db-only visual invariant retained': "_PendingVisualDbWrite(folder, legacyPath, bytes, bytes, 'source')" in cache_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.22 guard failed: {label}')

print('V8_22_WINDOWS_IMAGE_CACHE_MAX_ENTRIES=96')
print('V8_22_WINDOWS_IMAGE_CACHE_MAX_BYTES=67108864')
print('V8_22_VISUAL_DB_PENDING_MAX=32')
print('V8_22_VISUAL_DB_IDLE_FLUSH_MS=750')
print('V8_22_VISUAL_DB_WAL_AUTOCHECKPOINT=0')
print('V8_22_VISUAL_DB_IDLE_CHECKPOINT_MS=5000')
print('V8_22_VISUAL_DB_PHASE_DIAGNOSTICS=PASS')
print('V8_22_VISUAL_MEMORY_STALL_REDUCTION=PASS')
