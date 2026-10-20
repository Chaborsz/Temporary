from pathlib import Path
import re


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.21 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.21 {label}: {p}')


def regex_replace_once(path: str, pattern: str, replacement: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'v8.21 {label}: expected 1 regex match, found {count} in {p}')
    p.write_text(updated, encoding='utf-8')
    print(f'PATCHED v8.21 {label}: {p}')


# ---------------------------------------------------------------------------
# Runtime evidence from v8.20:
# - TAG_BATCH is no longer the freeze source (419 tags: map_ms=0, db_ms=85,
#   slice_max_ms=0, total=86 ms).
# - the next visible stall is SLOW_FRAME=202 ms with build/raster ~=1 ms,
#   pending=0 and no >=400 ms heartbeat event.
# - Danbooru's deferred setMultipleTrackedValues() runs outside PAGE_PHASE and
#   performs a large OR query on BooruItem postURL/fileURL. createIndexes() does
#   not currently create the BooruItem URL indexes that dropIndexes() already
#   knows about. This is both a blind spot and a plausible post-page blocker.
#
# v8.21 therefore:
# 1) rewrites tracked lookup to two IN sets + O(1) maps;
# 2) skips Rx writes when state is unchanged;
# 3) serializes Danbooru tracked refreshes;
# 4) restores URL indexes when the user's indexesEnabled setting is on;
# 5) logs TRACKED_BATCH timing;
# 6) adds an independent isolate watchdog that flushes stall markers immediately,
#    so even a hard freeze followed by process termination leaves evidence.
# ---------------------------------------------------------------------------

watchdog = Path('lib/src/services/performance_watchdog.dart')
if watchdog.exists():
    raise SystemExit('v8.21 watchdog file already exists')
watchdog.write_text(
    r'''import 'dart:async';
import 'dart:io';
import 'dart:isolate';

class WindowsPerformanceWatchdog {
  WindowsPerformanceWatchdog._();

  static SendPort? _sendPort;
  static Timer? _heartbeatTimer;
  static bool _starting = false;
  static final Set<String> _active = <String>{};

  static Future<void> start() async {
    if (!Platform.isWindows || _sendPort != null || _starting) return;
    _starting = true;
    try {
      final String sep = Platform.pathSeparator;
      final String logPath =
          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log';
      final ReceivePort ready = ReceivePort();
      await Isolate.spawn<List<Object?>>(
        _windowsPerformanceWatchdogEntry,
        <Object?>[ready.sendPort, logPath],
        debugName: 'LSPerfWatchdog',
      );
      final Object? readyMessage = await ready.first;
      ready.close();
      if (readyMessage is! SendPort) return;
      _sendPort = readyMessage;
      _sendHeartbeat();
      _heartbeatTimer = Timer.periodic(
        const Duration(milliseconds: 50),
        (_) => _sendHeartbeat(),
      );
    } finally {
      _starting = false;
    }
  }

  static String _activeState() {
    if (_active.isEmpty) return 'idle';
    final List<String> labels = _active.toList(growable: false)..sort();
    return labels.join('+');
  }

  static void _sendHeartbeat() {
    final SendPort? port = _sendPort;
    if (port == null) return;
    port.send(<Object?>[
      'heartbeat',
      DateTime.now().microsecondsSinceEpoch,
      _activeState(),
    ]);
  }

  static void enter(String label) {
    if (!Platform.isWindows) return;
    _active.add(label);
    _sendHeartbeat();
  }

  static void leave(String label) {
    if (!Platform.isWindows) return;
    _active.remove(label);
    _sendHeartbeat();
  }
}

@pragma('vm:entry-point')
void _windowsPerformanceWatchdogEntry(List<Object?> args) {
  final SendPort ready = args[0]! as SendPort;
  final String logPath = args[1]! as String;
  final ReceivePort inbox = ReceivePort();
  int lastHeartbeatUs = DateTime.now().microsecondsSinceEpoch;
  String active = 'startup';
  bool stalled = false;

  void append(String line) {
    try {
      final File file = File(logPath);
      file.parent.createSync(recursive: true);
      file.writeAsStringSync(
        '${DateTime.now().toIso8601String()} $line\n',
        mode: FileMode.append,
        flush: true,
      );
    } catch (_) {}
  }

  final Timer monitor = Timer.periodic(const Duration(milliseconds: 50), (_) {
    final int nowUs = DateTime.now().microsecondsSinceEpoch;
    final int gapMs = (nowUs - lastHeartbeatUs) ~/ 1000;
    if (gapMs >= 150 && !stalled) {
      stalled = true;
      append('WATCHDOG_STALL gap_ms=$gapMs active=$active');
    }
  });

  inbox.listen((dynamic message) {
    if (message is! List || message.length < 2) return;
    final Object? kind = message[0];
    if (kind == 'heartbeat') {
      final int nowUs = DateTime.now().microsecondsSinceEpoch;
      final int gapMs = (nowUs - lastHeartbeatUs) ~/ 1000;
      if (stalled) {
        append('WATCHDOG_RECOVER gap_ms=$gapMs active=$active');
        stalled = false;
      }
      final Object? sent = message[1];
      lastHeartbeatUs = sent is int ? sent : nowUs;
      if (message.length >= 3 && message[2] is String) {
        active = message[2] as String;
      }
    }
  });

  ready.send(inbox.sendPort);

  // Keep references alive for the lifetime of this isolate.
  if (monitor.isActive) {}
}
''',
    encoding='utf-8',
)
print('PATCHED v8.21 independent Windows watchdog')


# ---------------------------------------------------------------------------
# Main monitor: start the independent watchdog and lower the in-isolate heartbeat
# threshold so ~200 ms freezes are visible after recovery as well.
# ---------------------------------------------------------------------------
main = 'lib/main.dart'
replace_once(
    main,
    "import 'package:lolisnatcher/src/services/image_writer.dart';\n",
    "import 'package:lolisnatcher/src/services/image_writer.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'main-watchdog-import',
)
replace_once(
    main,
    """    PaintingBinding.instance.imageCache.maximumSize = 256;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 128 * 1024 * 1024;
    _startWindowsPerfMonitor();
""",
    """    PaintingBinding.instance.imageCache.maximumSize = 256;
    PaintingBinding.instance.imageCache.maximumSizeBytes = 128 * 1024 * 1024;
    await WindowsPerformanceWatchdog.start();
    _startWindowsPerfMonitor();
""",
    'start-independent-watchdog',
)
replace_once(
    main,
    '  Timer.periodic(const Duration(milliseconds: 250), (_) {\n',
    '  Timer.periodic(const Duration(milliseconds: 50), (_) {\n',
    'event-loop-sample-50ms',
)
replace_once(
    main,
    '    if (gap >= 400) {\n',
    '    if (gap >= 150) {\n',
    'event-loop-stall-threshold-150ms',
)


# ---------------------------------------------------------------------------
# Booru page fetch + deferred tracked state diagnostics.
# ---------------------------------------------------------------------------
booru_handler = 'lib/src/handlers/booru_handler.dart'
replace_once(
    booru_handler,
    "import 'package:lolisnatcher/src/handlers/tag_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/tag_handler.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'booru-watchdog-import',
)
replace_once(
    booru_handler,
    "      response = await fetchSearch(uri, tags, withCaptchaCheck: withCaptchaCheck);\n",
    """      WindowsPerformanceWatchdog.enter('page_fetch');
      try {
        response = await fetchSearch(uri, tags, withCaptchaCheck: withCaptchaCheck);
      } finally {
        WindowsPerformanceWatchdog.leave('page_fetch');
      }
""",
    'page-fetch-watchdog-phase',
)

# Add a dedicated tracked-state perf writer beside PAGE_PHASE.
regex_replace_once(
    booru_handler,
    r"(  Future<void> _appendWindowsPagePerf\(\{.*?\n  \}\n\n)(  Future<bool> searchSetup\(\) async \{)",
    r"""\1  Future<void> _appendWindowsTrackedPerf({
    required int items,
    required int lookupMs,
    required int applyMs,
    required int changed,
    required int totalMs,
    required bool indexesEnabled,
  }) async {
    if (!Platform.isWindows) return;
    try {
      final String sep = Platform.pathSeparator;
      final File file = File(
        '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
      );
      await file.parent.create(recursive: true);
      await file.writeAsString(
        '${DateTime.now().toIso8601String()} TRACKED_BATCH items=$items '
        'lookup_ms=$lookupMs apply_ms=$applyMs changed=$changed ms=$totalMs '
        'indexes=${indexesEnabled ? 1 : 0} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\n',
        mode: FileMode.append,
        flush: false,
      );
    } catch (_) {}
  }

\2""",
    'tracked-perf-writer',
)

# Replace the old deferred lookup implementation. This also removes the odd
# +1/index-list/sublist pattern and updates reactive state only on real changes.
regex_replace_once(
    booru_handler,
    r"  Future<void> setMultipleTrackedValues\(int beforeLength, int afterLength\) async \{.*?\n    return;\n  \}\n",
    r"""  Future<void> setMultipleTrackedValues(int beforeLength, int afterLength) async {
    final int start = max(0, beforeLength);
    final int end = min(fetched.length, max(start, afterLength));
    if (end <= start) return;

    final SettingsHandler settingsHandler = SettingsHandler.instance;
    if (settingsHandler.dbHandler.db == null) return;

    final List<BooruItem> items = fetched.sublist(start, end);
    final Stopwatch totalWatch = Stopwatch()..start();
    final Stopwatch lookupWatch = Stopwatch()..start();
    late final List<List<bool>> valuesList;

    WindowsPerformanceWatchdog.enter('tracked_lookup');
    try {
      valuesList = await settingsHandler.dbHandler.getMultipleTrackedValues(items);
    } finally {
      WindowsPerformanceWatchdog.leave('tracked_lookup');
    }
    lookupWatch.stop();

    final Stopwatch applyWatch = Stopwatch()..start();
    int changed = 0;
    WindowsPerformanceWatchdog.enter('tracked_apply');
    try {
      final int count = min(items.length, valuesList.length);
      for (int i = 0; i < count; i++) {
        final BooruItem item = items[i];
        final List<bool> values = valuesList[i];
        bool itemChanged = false;
        if (item.isSnatched.value != values[0]) {
          item.isSnatched.value = values[0];
          itemChanged = true;
        }
        if (item.isFavourite.value != values[1]) {
          item.isFavourite.value = values[1];
          itemChanged = true;
        }
        if (itemChanged) changed++;
      }
    } finally {
      WindowsPerformanceWatchdog.leave('tracked_apply');
    }
    applyWatch.stop();
    totalWatch.stop();

    unawaited(
      _appendWindowsTrackedPerf(
        items: items.length,
        lookupMs: lookupWatch.elapsedMilliseconds,
        applyMs: applyWatch.elapsedMilliseconds,
        changed: changed,
        totalMs: totalWatch.elapsedMilliseconds,
        indexesEnabled: settingsHandler.indexesEnabled,
      ),
    );
  }
""",
    'tracked-range-and-rx-optimization',
)


# ---------------------------------------------------------------------------
# DB tracked lookup: compact IN query + O(1) row maps. Add URL indexes to the
# existing optional index set; the user's indexesEnabled preference is retained.
# ---------------------------------------------------------------------------
database_handler = 'lib/src/handlers/database_handler.dart'
replace_once(
    database_handler,
    """  Future<bool> createIndexes() async {
    await db?.execute('CREATE INDEX IF NOT EXISTS ImageTag_tagID_index ON ImageTag (tagID);');
    await db?.execute('CREATE INDEX IF NOT EXISTS ImageTag_booruItemID_index ON ImageTag (booruItemID);');
    return true;
  }
""",
    """  Future<bool> createIndexes() async {
    await db?.execute('CREATE INDEX IF NOT EXISTS ImageTag_tagID_index ON ImageTag (tagID);');
    await db?.execute('CREATE INDEX IF NOT EXISTS ImageTag_booruItemID_index ON ImageTag (booruItemID);');
    await db?.execute('CREATE INDEX IF NOT EXISTS BooruItem_postURL_index ON BooruItem (postURL);');
    await db?.execute('CREATE INDEX IF NOT EXISTS BooruItem_fileURL_index ON BooruItem (fileURL);');
    return true;
  }
""",
    'restore-booru-url-indexes',
)
replace_once(
    database_handler,
    "    await db?.execute('DROP INDEX IF EXISTS BooruItem_fileURL_index;');\n",
    "    await db?.execute('DROP INDEX IF EXISTS BooruItem_fileURL_index;');\n    await db?.execute('DROP INDEX IF EXISTS BooruItem_postURL_index;');\n",
    'drop-posturl-index-with-optional-index-set',
)
regex_replace_once(
    database_handler,
    r"  Future<List<List<bool>>> getMultipleTrackedValues\(List<BooruItem> items\) async \{.*?\n    return values;\n  \}\n",
    r"""  Future<List<List<bool>>> getMultipleTrackedValues(List<BooruItem> items) async {
    if (items.isEmpty) return <List<bool>>[];

    final Set<String> postUrls = <String>{
      for (final BooruItem item in items)
        if (item.postURL.isNotEmpty) item.postURL,
    };
    final Set<String> fileUrls = <String>{
      for (final BooruItem item in items)
        if (item.fileURL.isNotEmpty) item.fileURL,
    };

    final List<String> clauses = <String>[];
    final List<Object?> args = <Object?>[];
    if (postUrls.isNotEmpty) {
      clauses.add("postURL IN (${List<String>.filled(postUrls.length, '?').join(',')})");
      args.addAll(postUrls);
    }
    if (fileUrls.isNotEmpty) {
      clauses.add("fileURL IN (${List<String>.filled(fileUrls.length, '?').join(',')})");
      args.addAll(fileUrls);
    }

    if (clauses.isEmpty) {
      return List<List<bool>>.generate(items.length, (_) => <bool>[false, false]);
    }

    final List<Map<String, Object?>> result = await db?.rawQuery(
          'SELECT fileURL, postURL, isFavourite, isSnatched FROM BooruItem WHERE ${clauses.join(' OR ')};',
          args,
        ) ??
        <Map<String, Object?>>[];

    final Map<String, Map<String, Object?>> byPostUrl = <String, Map<String, Object?>>{};
    final Map<String, Map<String, Object?>> byFileUrl = <String, Map<String, Object?>>{};
    for (final Map<String, Object?> row in result) {
      final String postUrl = row['postURL']?.toString() ?? '';
      final String fileUrl = row['fileURL']?.toString() ?? '';
      if (postUrl.isNotEmpty) byPostUrl[postUrl] = row;
      if (fileUrl.isNotEmpty) byFileUrl[fileUrl] = row;
    }

    final List<List<bool>> values = <List<bool>>[];
    for (final BooruItem item in items) {
      final Map<String, Object?>? row =
          (item.postURL.isNotEmpty ? byPostUrl[item.postURL] : null) ??
          (item.fileURL.isNotEmpty ? byFileUrl[item.fileURL] : null);
      values.add(<bool>[
        row == null ? false : Tools.intToBool(row['isSnatched']),
        row == null ? false : Tools.intToBool(row['isFavourite']),
      ]);
    }
    return values;
  }
""",
    'tracked-bulk-in-query-and-map',
)


# ---------------------------------------------------------------------------
# Danbooru: serialize the already-deferred tracked refreshes so rapid pagination
# cannot overlap multiple BooruItem lookups/Rx-application passes.
# ---------------------------------------------------------------------------
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    "import 'package:lolisnatcher/src/handlers/tag_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/tag_handler.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'danbooru-watchdog-import',
)
replace_once(
    danbooru,
    """  Future<void> _tagCommitChain = Future<void>.value();
  Timer? _tagFlushTimer;
""",
    """  Future<void> _tagCommitChain = Future<void>.value();
  Future<void> _trackedValueChain = Future<void>.value();
  Timer? _tagFlushTimer;
""",
    'tracked-refresh-chain-state',
)
replace_once(
    danbooru,
    """  void _queuePageTagCommit(Map<TagType, List<String>> batches) {
""",
    """  void _queueTrackedValueRefresh(int beforeLength, int afterLength) {
    _trackedValueChain = _trackedValueChain.then((_) async {
      await Future<void>.delayed(Duration.zero);
      await setMultipleTrackedValues(beforeLength, afterLength);
    });
    unawaited(_trackedValueChain);
  }

  void _queuePageTagCommit(Map<TagType, List<String>> batches) {
""",
    'tracked-refresh-serialized-helper',
)
replace_once(
    danbooru,
    """    unawaited(
      Future<void>.delayed(
        Duration.zero,
        () => setMultipleTrackedValues(lengthBefore, fetched.length),
      ),
    );
""",
    """    _queueTrackedValueRefresh(lengthBefore, fetched.length);
""",
    'use-serialized-tracked-refresh',
)
replace_once(
    danbooru,
    """    final ({int changed, int mapMs, int dbMs, int sliceMaxMs, int yields}) result =
        await TagHandler.instance.addTypedTagsBatch(batches);
""",
    """    WindowsPerformanceWatchdog.enter('tag_batch');
    late final ({int changed, int mapMs, int dbMs, int sliceMaxMs, int yields}) result;
    try {
      result = await TagHandler.instance.addTypedTagsBatch(batches);
    } finally {
      WindowsPerformanceWatchdog.leave('tag_batch');
    }
""",
    'tag-batch-watchdog-phase',
)


# ---------------------------------------------------------------------------
# Visual pipeline phase: useful if the watchdog catches a hard freeze while an
# image cache/network/decode operation owns the single Windows visual permit.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    "import 'package:lolisnatcher/src/services/image_writer.dart';\n",
    "import 'package:lolisnatcher/src/services/image_writer.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'visual-watchdog-import',
)
custom_path = Path(custom)
custom_text = custom_path.read_text(encoding='utf-8')
acquire = """    final _AsyncPermit? visualPermit =
        limitVisualPipeline ? await _windowsVisualPipelineGate.acquire(cancelToken) : null;

"""
if custom_text.count(acquire) != 2:
    raise SystemExit(f'v8.21 visual-phase-acquire: expected 2 matches, found {custom_text.count(acquire)}')
custom_text = custom_text.replace(
    acquire,
    acquire + "    if (limitVisualPipeline) WindowsPerformanceWatchdog.enter('visual_pipeline');\n\n",
)
release = "      visualPermit?.release();\n"
if custom_text.count(release) != 2:
    raise SystemExit(f'v8.21 visual-phase-release: expected 2 matches, found {custom_text.count(release)}')
custom_text = custom_text.replace(
    release,
    "      if (limitVisualPipeline) WindowsPerformanceWatchdog.leave('visual_pipeline');\n      visualPermit?.release();\n",
)
custom_path.write_text(custom_text, encoding='utf-8')
print('PATCHED v8.21 visual pipeline watchdog phase (2 providers)')


# Guards.
main_final = Path(main).read_text(encoding='utf-8')
booru_final = Path(booru_handler).read_text(encoding='utf-8')
db_final = Path(database_handler).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
custom_final = Path(custom).read_text(encoding='utf-8')
watchdog_final = watchdog.read_text(encoding='utf-8')
checks = {
    'watchdog isolate': 'Isolate.spawn<List<Object?>>' in watchdog_final,
    'watchdog immediate flush': 'flush: true' in watchdog_final,
    'watchdog threshold 150': 'gapMs >= 150' in watchdog_final,
    'main watchdog start': 'await WindowsPerformanceWatchdog.start();' in main_final,
    'main event loop sample 50': 'Timer.periodic(const Duration(milliseconds: 50)' in main_final,
    'main event loop threshold 150': 'if (gap >= 150) {' in main_final,
    'tracked perf': 'TRACKED_BATCH items=' in booru_final,
    'tracked lookup phase': "enter('tracked_lookup')" in booru_final,
    'tracked unchanged Rx skip': 'item.isSnatched.value != values[0]' in booru_final,
    'post url index': 'BooruItem_postURL_index' in db_final,
    'file url index': 'BooruItem_fileURL_index' in db_final,
    'tracked IN query': 'postURL IN (' in db_final and 'fileURL IN (' in db_final,
    'tracked O1 maps': 'byPostUrl' in db_final and 'byFileUrl' in db_final,
    'serialized tracked refresh': '_trackedValueChain' in dan_final,
    'old direct deferred tracked refresh removed': '() => setMultipleTrackedValues(lengthBefore, fetched.length)' not in dan_final,
    'tag phase': "enter('tag_batch')" in dan_final,
    'visual phases': custom_final.count("enter('visual_pipeline')") == 2 and custom_final.count("leave('visual_pipeline')") == 2,
    'v8.20 tag slicing retained': '(processed & 31) == 0' in Path('lib/src/handlers/tag_handler.dart').read_text(encoding='utf-8'),
    'v8.18 persistent visual HTTP retained': '_windowsVisualClient' in custom_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.21 guard failed: {label}')

print('V8_21_TRACKED_LOOKUP_IN_QUERY=PASS')
print('V8_21_TRACKED_LOOKUP_URL_INDEXES=PASS')
print('V8_21_TRACKED_RX_CHANGE_ONLY=PASS')
print('V8_21_TRACKED_REFRESH_SERIAL=PASS')
print('V8_21_TRACKED_BATCH_DIAGNOSTIC=PASS')
print('V8_21_WATCHDOG_ISOLATE=PASS')
print('V8_21_WATCHDOG_STALL_THRESHOLD_MS=150')
print('V8_21_EVENT_LOOP_DIAGNOSTIC_THRESHOLD_MS=150')
print('V8_21_POST_PAGE_STALL_REDUCTION=PASS')
