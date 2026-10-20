from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.11 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.11 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) Stop obsolete/offscreen requests from poisoning the bounded visual queue.
#    v8.10 bounded work, but a cancelled tile could remain queued until it got a
#    permit. Make waiters cancellation-aware and wake cancelled loads promptly.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'

replace_once(
    custom,
    """class _AsyncGate {
  _AsyncGate(this.maxActive);

  final int maxActive;
  int _active = 0;
  final List<Completer<_AsyncPermit>> _waiters = <Completer<_AsyncPermit>>[];

  Future<_AsyncPermit> acquire() {
    if (_active < maxActive) {
      _active++;
      return Future<_AsyncPermit>.value(_AsyncPermit(_release));
    }

    final Completer<_AsyncPermit> completer = Completer<_AsyncPermit>();
    _waiters.add(completer);
    return completer.future;
  }

  void _release() {
    if (_waiters.isNotEmpty) {
      final Completer<_AsyncPermit> next = _waiters.removeAt(0);
      next.complete(_AsyncPermit(_release));
      return;
    }
    if (_active > 0) _active--;
  }
}
""",
    """class _AsyncWaiter {
  _AsyncWaiter(this.completer, this.cancelToken);

  final Completer<_AsyncPermit> completer;
  final CancelToken? cancelToken;
}

class _AsyncGate {
  _AsyncGate(this.maxActive);

  final int maxActive;
  int _active = 0;
  final List<_AsyncWaiter> _waiters = <_AsyncWaiter>[];

  Future<_AsyncPermit> acquire(CancelToken? cancelToken) {
    if (cancelToken?.isCancelled ?? false) {
      return Future<_AsyncPermit>.value(_AsyncPermit(() {}));
    }

    if (_active < maxActive) {
      _active++;
      return Future<_AsyncPermit>.value(_AsyncPermit(_release));
    }

    final Completer<_AsyncPermit> completer = Completer<_AsyncPermit>();
    final _AsyncWaiter waiter = _AsyncWaiter(completer, cancelToken);
    _waiters.add(waiter);

    if (cancelToken != null) {
      unawaited(
        cancelToken.whenCancel.then((_) {
          if (_waiters.remove(waiter) && !completer.isCompleted) {
            completer.complete(_AsyncPermit(() {}));
          }
        }),
      );
    }
    return completer.future;
  }

  void _release() {
    while (_waiters.isNotEmpty) {
      final _AsyncWaiter next = _waiters.removeAt(0);
      if (next.completer.isCompleted) continue;
      if (next.cancelToken?.isCancelled ?? false) {
        next.completer.complete(_AsyncPermit(() {}));
        continue;
      }
      next.completer.complete(_AsyncPermit(_release));
      return;
    }
    if (_active > 0) _active--;
  }
}
""",
    'cancel-aware-visual-gate',
)

p = Path(custom)
text = p.read_text(encoding='utf-8')
old = """    final _AsyncPermit? visualPermit =
        limitVisualPipeline ? await _windowsVisualPipelineGate.acquire() : null;

    try {
"""
new = """    final _AsyncPermit? visualPermit =
        limitVisualPipeline ? await _windowsVisualPipelineGate.acquire(cancelToken) : null;

    if (visualPermit != null && (cancelToken?.isCancelled ?? false)) {
      visualPermit.release();
      throw DioException(
        requestOptions: RequestOptions(path: key.url),
        type: DioExceptionType.cancel,
        error: 'Cancelled while waiting for Windows visual pipeline',
      );
    }

    try {
"""
count = text.count(old)
if count != 2:
    raise SystemExit(f'v8.11 cancel-after-gate: expected 2 matches, found {count}')
p.write_text(text.replace(old, new), encoding='utf-8')
print('PATCHED v8.11 cancel-after-gate (2 providers)')


# ---------------------------------------------------------------------------
# 2) Stop manually evicting every grid tile from Flutter ImageCache. That forced
#    repeated native decodes when a tile re-entered the viewport. Let Flutter's
#    bounded LRU cache decide what to retain instead.
# ---------------------------------------------------------------------------
replace_once(
    'lib/src/widgets/thumbnail/thumbnail.dart',
    """    // evict from memory cache only when in grid
    if (widget.isStandalone) {
      mainProvider.value?.evict();
      mainProvider.value = null;
      extraProvider.value?.evict();
      extraProvider.value = null;
    }
""",
    """    // Keep recently decoded grid images in Flutter's bounded LRU cache.
    // Explicit eviction here caused decode churn when scrolling back/forth.
    if (widget.isStandalone) {
      mainProvider.value = null;
      extraProvider.value = null;
    }
""",
    'retain-recent-grid-images',
)


# ---------------------------------------------------------------------------
# 3) A/B WebP out of the runtime hot path completely. New thumbnails are stored
#    as the source payload in SQLite; existing WebP thumbnail rows are discarded
#    once by DB v4 so this build no longer depends on background WebP encode.
# ---------------------------------------------------------------------------
cache = 'lib/src/services/compressed_visual_cache.dart'
replace_once(cache, '        version: 3,\n', '        version: 4,\n', 'visual-cache-db-v4')

replace_once(
    cache,
    """          if (oldVersion < 3) {
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
""",
    """          if (oldVersion < 3) {
            final List<Map<String, Object?>> columns = await db.rawQuery('PRAGMA table_info(VisualCache)');
            final bool hasCodec = columns.any((row) => row['name'] == 'codec');
            if (!hasCodec) {
              await db.execute("ALTER TABLE VisualCache ADD COLUMN codec TEXT NOT NULL DEFAULT 'source'");
            }
            await db.delete(
              'VisualCache',
              where: 'folder = ?',
              whereArgs: <Object?>['thumbnails'],
            );
          }
          if (oldVersion < 4) {
            // v8.11 A/B: remove only old WebP thumbnail rows. Account/settings,
            // downloads and every non-thumbnail cache entry remain untouched.
            await db.delete(
              'VisualCache',
              where: "folder = ? AND codec LIKE 'webp%'",
              whereArgs: <Object?>['thumbnails'],
            );
          }
""",
    'purge-old-webp-thumbnail-rows-once',
)

replace_once(
    cache,
    """    try {
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
""",
    """    try {
      // v8.11: persist source bytes only. This deliberately removes image decode,
      // resize, isolate creation and WebP encode from background cache work.
      await _storeEntry(folder, legacyPath, bytes, bytes, 'source');
    } catch (_) {
      // Cache persistence is optional. A failed background write must never
      // block or fail the visible image load.
    } finally {
""",
    'disable-background-webp-conversion',
)

replace_once(
    'lib/src/pages/settings/save_cache_page.dart',
    r"Miniaturas WebP empaquetadas: Data\LoliSnatcher\cache\visual_cache.db",
    r"Miniaturas empaquetadas (formato fuente): Data\LoliSnatcher\cache\visual_cache.db",
    'source-thumbnail-cache-label',
)


# ---------------------------------------------------------------------------
# 4) Bounded in-memory cache + very low overhead stall diagnostics.
#    performance-stalls.log contains no URLs, credentials or response bodies.
# ---------------------------------------------------------------------------
main = 'lib/main.dart'
monitor = r'''final Stopwatch _windowsPerfClock = Stopwatch();
final List<String> _windowsPerfLines = <String>[];
Future<void> _windowsPerfWriteChain = Future<void>.value();
File? _windowsPerfFile;

void _queueWindowsPerfLine(String message) {
  if (!Platform.isWindows) return;
  _windowsPerfLines.add('${DateTime.now().toIso8601String()} $message');
}

void _flushWindowsPerfLines() {
  final File? file = _windowsPerfFile;
  if (file == null || _windowsPerfLines.isEmpty) return;
  final String payload = '${_windowsPerfLines.join('\n')}\n';
  _windowsPerfLines.clear();
  _windowsPerfWriteChain = _windowsPerfWriteChain.then((_) async {
    try {
      await file.writeAsString(payload, mode: FileMode.append, flush: false);
    } catch (_) {}
  });
}

void _startWindowsPerfMonitor() {
  if (!Platform.isWindows || _windowsPerfClock.isRunning) return;

  final String sep = Platform.pathSeparator;
  _windowsPerfFile = File(
    '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
  );
  try {
    _windowsPerfFile!.parent.createSync(recursive: true);
  } catch (_) {}

  _windowsPerfClock.start();
  int lastHeartbeat = _windowsPerfClock.elapsedMilliseconds;
  _queueWindowsPerfLine(
    'SESSION_START cache_max_entries=${PaintingBinding.instance.imageCache.maximumSize} '
    'cache_max_bytes=${PaintingBinding.instance.imageCache.maximumSizeBytes}',
  );

  WidgetsBinding.instance.addTimingsCallback((List<FrameTiming> timings) {
    for (final FrameTiming timing in timings) {
      final int buildMs = timing.buildDuration.inMilliseconds;
      final int rasterMs = timing.rasterDuration.inMilliseconds;
      final int totalMs = timing.totalSpan.inMilliseconds;
      if (totalMs >= 100 || buildMs >= 50 || rasterMs >= 50) {
        final ImageCache cache = PaintingBinding.instance.imageCache;
        _queueWindowsPerfLine(
          'SLOW_FRAME total_ms=$totalMs build_ms=$buildMs raster_ms=$rasterMs '
          'live=${cache.liveImageCount} pending=${cache.pendingImageCount} '
          'entries=${cache.currentSize} cache_mb=${cache.currentSizeBytes ~/ (1024 * 1024)} '
          'rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
        );
      }
    }
  });

  Timer.periodic(const Duration(milliseconds: 250), (_) {
    final int now = _windowsPerfClock.elapsedMilliseconds;
    final int gap = now - lastHeartbeat;
    lastHeartbeat = now;
    if (gap >= 650) {
      final ImageCache cache = PaintingBinding.instance.imageCache;
      _queueWindowsPerfLine(
        'EVENT_LOOP_STALL gap_ms=$gap live=${cache.liveImageCount} '
        'pending=${cache.pendingImageCount} entries=${cache.currentSize} '
        'cache_mb=${cache.currentSizeBytes ~/ (1024 * 1024)} '
        'rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
      );
    }
  });

  Timer.periodic(const Duration(seconds: 2), (_) => _flushWindowsPerfLines());
  _flushWindowsPerfLines();
}

'''

replace_once(
    main,
    'void main() async {\n',
    monitor + 'void main() async {\n',
    'windows-stall-monitor',
)

replace_once(
    main,
    """  CustomWidgetsBinding.ensureInitialized();

  if (Platform.isWindows || Platform.isLinux) {
""",
    """  CustomWidgetsBinding.ensureInitialized();

  if (Platform.isWindows) {
    // Retain a bounded working set so scrolling back does not constantly decode
    // the same thumbnails again after v8.11 removes explicit per-tile eviction.
    PaintingBinding.instance.imageCache.maximumSize = 256;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 128 * 1024 * 1024;
    _startWindowsPerfMonitor();
  }

  if (Platform.isWindows || Platform.isLinux) {
""",
    'windows-bounded-image-cache-and-monitor-start',
)


# Guards.
custom_text = Path(custom).read_text(encoding='utf-8')
thumb_text = Path('lib/src/widgets/thumbnail/thumbnail.dart').read_text(encoding='utf-8')
cache_text = Path(cache).read_text(encoding='utf-8')
main_text = Path(main).read_text(encoding='utf-8')
checks = {
    'cancel-aware gate': 'Future<_AsyncPermit> acquire(CancelToken? cancelToken)' in custom_text,
    'cancel waiters removed': '_waiters.remove(waiter)' in custom_text,
    'post-gate cancellation': custom_text.count("Cancelled while waiting for Windows visual pipeline") == 2,
    'no grid explicit eviction': 'mainProvider.value?.evict();' not in thumb_text and 'extraProvider.value?.evict();' not in thumb_text,
    'db v4': 'version: 4' in cache_text,
    'old webp rows purged': "codec LIKE 'webp%'" in cache_text,
    'background webp disabled': "await _storeEntry(folder, legacyPath, bytes, bytes, 'source');" in cache_text,
    'webp encode no longer called by persistence': 'final Uint8List? webp = await _WebPQueue.encode(bytes, maxDimension: 512);' not in cache_text,
    'image cache bounded': 'imageCache.maximumSize = 256;' in main_text and '128 * 1024 * 1024' in main_text,
    'stall monitor': 'EVENT_LOOP_STALL' in main_text and 'SLOW_FRAME' in main_text and 'performance-stalls.log' in main_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.11 guard failed: {label}')

print('V8_11_CANCEL_AWARE_VISUAL_GATE=PASS')
print('V8_11_IMAGECACHE_LRU_REUSE=PASS')
print('V8_11_WEBP_RUNTIME_DISABLED=PASS')
print('V8_11_VISUAL_CACHE_DB_V4=PASS')
print('V8_11_STALL_DIAGNOSTICS=PASS')
print('V8_11_FREEZE_ROOTCAUSE_PATCH=PASS')
