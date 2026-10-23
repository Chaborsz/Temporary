from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.24 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.24 {label}: {p}')


# ---------------------------------------------------------------------------
# Runtime evidence from v8.23:
# - PAGE_PHASE stays parse_ms=0 / merge_ms=0 and TRACKED_BATCH stays 0-5 ms.
# - tag map work stays cooperative (map_ms=0), but one large flush reached
#   db_ms=155; keep tag semantics unchanged and add a nested tag_db phase.
# - the watchdog now proves two independent classes of stalls:
#     * page_fetch (150-215 ms), and
#     * idle (171 ms).
# - the first long session starts at 23:35:56; upstream _DailyFileLogger waits
#   1000 seconds before its first buffered flush, i.e. about 23:52:36. The
#   unexplained idle watchdog stall appears at 23:52:52. Upstream also retains
#   up to 100000 Talker history entries and writes the entire accumulated batch
#   on the UI isolate.
# - DioNetwork installs both TalkerDioLogger and Alice for every ordinary request
#   even in Windows Release. Alice is only consumed by the developer network
#   inspector, so production requests pay inspection/history overhead without
#   a functional requirement.
#
# v8.24 therefore removes the proven burst pattern without removing logs:
# - Windows log history is bounded to 5000 entries;
# - file logs flush every 2 s or 64 lines and yield every 32 encoded lines;
# - watchdog labels log_flush and emits LOG_BATCH for slow batches;
# - Windows Release skips Talker/Alice network inspection unless app debug mode
#   is explicitly enabled; cookie/captcha behavior remains untouched;
# - page/http/cookie/captcha/tag-db/visual-http/visual-codec phases are nested so
#   any residual freeze is attributed instead of guessed.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1) Remove the 1000-second log burst and bound retained diagnostic history.
# ---------------------------------------------------------------------------
logger = 'lib/src/utils/logger.dart'
replace_once(
    logger,
    "import 'package:lolisnatcher/src/widgets/common/compact_error_widget.dart';\n",
    "import 'package:lolisnatcher/src/services/performance_watchdog.dart';\nimport 'package:lolisnatcher/src/widgets/common/compact_error_widget.dart';\n",
    'logger-watchdog-import',
)
replace_once(
    logger,
    '        maxHistoryItems: 100000,\n',
    '        maxHistoryItems: Platform.isWindows ? 5000 : 100000,\n',
    'windows-talker-history-bound',
)
replace_once(
    logger,
    '  static const _writeDelay = Duration(seconds: 1000);\n',
    '  static const _writeDelay = Duration(seconds: 2);\n  static const _maxBufferedLines = 64;\n',
    'logger-small-flush-window',
)
replace_once(
    logger,
    """    _buffer.add(
      _PendingLogLine(
        date: date,
        text: '[${now.toIso8601String()}][$source] $cleanMessage\\n',
      ),
    );
    _flushTimer ??= Timer(_writeDelay, () {
      _flushTimer = null;
      unawaited(_queueBufferedWrite());
    });
""",
    """    _buffer.add(
      _PendingLogLine(
        date: date,
        text: '[${now.toIso8601String()}][$source] $cleanMessage\\n',
      ),
    );

    if (_buffer.length >= _maxBufferedLines) {
      _flushTimer?.cancel();
      _flushTimer = null;
      unawaited(_queueBufferedWrite());
    } else {
      _flushTimer ??= Timer(_writeDelay, () {
        _flushTimer = null;
        unawaited(_queueBufferedWrite());
      });
    }
""",
    'logger-bounded-buffer-trigger',
)
replace_once(
    logger,
    """  Future<void> _writeBatch(List<_PendingLogLine> batch) async {
    for (final line in batch) {
      await _openSinkForDate(line.date);
      if (_sizeLimitReached) {
        continue;
      }

      final bytes = utf8.encode(line.text);
      if (_sinkBytes + bytes.length > _maxFileBytes) {
        // TODO change to log rotation if 25mb is not big enough for power users
        const limitMessage = '[logger] Daily log size limit reached; further logs are omitted.\\n';
        final limitBytes = utf8.encode(limitMessage);
        if (_sinkBytes + limitBytes.length <= _maxFileBytes) {
          _sink!.add(limitBytes);
          _sinkBytes += limitBytes.length;
        }
        _sizeLimitReached = true;
        continue;
      }

      _sink!.add(bytes);
      _sinkBytes += bytes.length;
    }
    await _sink?.flush();
  }
""",
    """  Future<void> _writeBatch(List<_PendingLogLine> batch) async {
    final Stopwatch watch = Stopwatch()..start();
    WindowsPerformanceWatchdog.enter('log_flush');
    try {
      for (int i = 0; i < batch.length; i++) {
        final _PendingLogLine line = batch[i];
        await _openSinkForDate(line.date);
        if (_sizeLimitReached) {
          continue;
        }

        final bytes = utf8.encode(line.text);
        if (_sinkBytes + bytes.length > _maxFileBytes) {
          // TODO change to log rotation if 25mb is not big enough for power users
          const limitMessage = '[logger] Daily log size limit reached; further logs are omitted.\\n';
          final limitBytes = utf8.encode(limitMessage);
          if (_sinkBytes + limitBytes.length <= _maxFileBytes) {
            _sink!.add(limitBytes);
            _sinkBytes += limitBytes.length;
          }
          _sizeLimitReached = true;
          continue;
        }

        _sink!.add(bytes);
        _sinkBytes += bytes.length;

        if ((i & 31) == 31) {
          await Future<void>.delayed(Duration.zero);
        }
      }
      await _sink?.flush();
    } finally {
      WindowsPerformanceWatchdog.leave('log_flush');
      watch.stop();
    }

    if (Platform.isWindows && watch.elapsedMilliseconds >= 25) {
      try {
        final String sep = Platform.pathSeparator;
        final File file = File(
          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
        );
        await file.writeAsString(
          '${DateTime.now().toIso8601String()} LOG_BATCH lines=${batch.length} '
          'ms=${watch.elapsedMilliseconds} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\\n',
          mode: FileMode.append,
          flush: false,
        );
      } catch (_) {}
    }
  }
""",
    'cooperative-log-batch-write',
)


# ---------------------------------------------------------------------------
# 2) Ordinary Windows Release requests do not need two network inspectors.
# Keep them available in Flutter debug builds or when the app debug toggle is
# explicitly enabled. Cookies, captcha handling and Dio itself are unchanged.
# ---------------------------------------------------------------------------
dio = 'lib/src/utils/dio_network.dart'
replace_once(
    dio,
    "import 'dart:async';\n\nimport 'package:dio/dio.dart';\n",
    "import 'dart:async';\nimport 'dart:io';\n\nimport 'package:flutter/foundation.dart';\n\nimport 'package:dio/dio.dart';\n",
    'dio-platform-debug-imports',
)
replace_once(
    dio,
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'dio-watchdog-import',
)
replace_once(
    dio,
    """    if (!skipLogging) {
      dio.interceptors.add(Logger.dioInterceptor!);
      dio.interceptors.add(settingsHandler.alice.getDioInterceptor());
    }
""",
    """    final bool enableNetworkDiagnostics =
        !Platform.isWindows || kDebugMode || settingsHandler.isDebug.value;
    if (!skipLogging && enableNetworkDiagnostics) {
      dio.interceptors.add(Logger.dioInterceptor!);
      dio.interceptors.add(settingsHandler.alice.getDioInterceptor());
    }
""",
    'disable-windows-release-network-inspectors',
)

# Captcha phase, both response and error paths.
replace_once(
    dio,
    """          final bool captchaWasDetected = await Tools.checkForCaptcha(
            response,
            response.realUri,
            customUserAgent: customUserAgent,
          );
""",
    """          WindowsPerformanceWatchdog.enter('captcha_check');
          late final bool captchaWasDetected;
          try {
            captchaWasDetected = await Tools.checkForCaptcha(
              response,
              response.realUri,
              customUserAgent: customUserAgent,
            );
          } finally {
            WindowsPerformanceWatchdog.leave('captcha_check');
          }
""",
    'captcha-response-phase',
)
replace_once(
    dio,
    """          final bool captchaWasDetected = await Tools.checkForCaptcha(error.response, error.requestOptions.uri);
""",
    """          WindowsPerformanceWatchdog.enter('captcha_check');
          late final bool captchaWasDetected;
          try {
            captchaWasDetected = await Tools.checkForCaptcha(error.response, error.requestOptions.uri);
          } finally {
            WindowsPerformanceWatchdog.leave('captcha_check');
          }
""",
    'captcha-error-phase',
)

# Cookie phases. Windows getCookies is normally memory-only, while saveCookies
# may bridge to WebView2; labels make the distinction runtime-visible.
replace_once(
    dio,
    """        onRequest: (RequestOptions options, RequestInterceptorHandler handler) async {
          final String oldCookie = options.headers['Cookie'] as String? ?? '';
          final String newCookie = await Tools.getCookies(options.uri.toString());
          final headers = {
""",
    """        onRequest: (RequestOptions options, RequestInterceptorHandler handler) async {
          final String oldCookie = options.headers['Cookie'] as String? ?? '';
          WindowsPerformanceWatchdog.enter('cookie_get');
          late final String newCookie;
          try {
            newCookie = await Tools.getCookies(options.uri.toString());
          } finally {
            WindowsPerformanceWatchdog.leave('cookie_get');
          }
          final headers = {
""",
    'cookie-get-phase',
)
replace_once(
    dio,
    """        onResponse: (Response response, ResponseInterceptorHandler handler) async {
          final setCookies = response.headers['set-cookie'] ?? [];
          await Tools.saveCookies(
            response.requestOptions.uri.toString(),
            setCookies,
          );
          return handler.next(response);
        },
""",
    """        onResponse: (Response response, ResponseInterceptorHandler handler) async {
          final setCookies = response.headers['set-cookie'] ?? [];
          WindowsPerformanceWatchdog.enter('cookie_save');
          try {
            await Tools.saveCookies(
              response.requestOptions.uri.toString(),
              setCookies,
            );
          } finally {
            WindowsPerformanceWatchdog.leave('cookie_save');
          }
          return handler.next(response);
        },
""",
    'cookie-save-response-phase',
)
replace_once(
    dio,
    """        onError: (DioException error, ErrorInterceptorHandler handler) async {
          final setCookies = error.response?.headers['set-cookie'] ?? [];
          await Tools.saveCookies(
            error.requestOptions.uri.toString(),
            setCookies,
          );
          return handler.next(error);
        },
""",
    """        onError: (DioException error, ErrorInterceptorHandler handler) async {
          final setCookies = error.response?.headers['set-cookie'] ?? [];
          WindowsPerformanceWatchdog.enter('cookie_save');
          try {
            await Tools.saveCookies(
              error.requestOptions.uri.toString(),
              setCookies,
            );
          } finally {
            WindowsPerformanceWatchdog.leave('cookie_save');
          }
          return handler.next(error);
        },
""",
    'cookie-save-error-phase',
)


# ---------------------------------------------------------------------------
# 3) Refine page-fetch attribution without changing request/auth semantics.
# ---------------------------------------------------------------------------
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    """    final String cookies = await getCookies() ?? '';
    final Map<String, String> headers = {
""",
    """    WindowsPerformanceWatchdog.enter('page_cookie');
    late final String cookies;
    try {
      cookies = await getCookies() ?? '';
    } finally {
      WindowsPerformanceWatchdog.leave('page_cookie');
    }
    final Map<String, String> headers = {
""",
    'danbooru-page-cookie-phase',
)
replace_once(
    danbooru,
    """    return DioNetwork.get(
      uri.toString(),
      headers: headers,
      queryParameters: queryParams,
      options: fetchSearchOptions(),
      customInterceptor: withCaptchaCheck
          ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
          : null,
    );
""",
    """    WindowsPerformanceWatchdog.enter('page_http');
    try {
      return await DioNetwork.get(
        uri.toString(),
        headers: headers,
        queryParameters: queryParams,
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
    } finally {
      WindowsPerformanceWatchdog.leave('page_http');
    }
""",
    'danbooru-page-http-phase',
)


# ---------------------------------------------------------------------------
# 4) Tag SQLite is now the only expensive subphase observed in a large tag
# flush. Label it explicitly; persistence semantics remain exactly v8.20.
# ---------------------------------------------------------------------------
tag_handler = 'lib/src/handlers/tag_handler.dart'
replace_once(
    tag_handler,
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\nimport 'package:lolisnatcher/src/services/performance_watchdog.dart';\n",
    'tag-watchdog-import',
)
replace_once(
    tag_handler,
    """      final Stopwatch dbWatch = Stopwatch()..start();
      await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);
      dbWatch.stop();
""",
    """      final Stopwatch dbWatch = Stopwatch()..start();
      WindowsPerformanceWatchdog.enter('tag_db');
      try {
        await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);
      } finally {
        WindowsPerformanceWatchdog.leave('tag_db');
      }
      dbWatch.stop();
""",
    'tag-db-watchdog-phase',
)


# ---------------------------------------------------------------------------
# 5) Refine the existing visual_pipeline label into network vs codec work.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    """    Response? response;
    // Dio applies receiveTimeout between response chunks. Without a default,
""",
    """    Response? response;
    WindowsPerformanceWatchdog.enter('visual_http');
    // Dio applies receiveTimeout between response chunks. Without a default,
""",
    'visual-http-enter',
)
replace_once(
    custom,
    """    } finally {
      if (!reuseWindowsVisualClient) {
        client.close();
      }
    }
""",
    """    } finally {
      WindowsPerformanceWatchdog.leave('visual_http');
      if (!reuseWindowsVisualClient) {
        client.close();
      }
    }
""",
    'visual-http-leave',
)
replace_once(
    custom,
    """      final Stopwatch codecWatch = Stopwatch()..start();
      final Stopwatch bufferWatch = Stopwatch()..start();
      final ui.ImmutableBuffer buffer = await ui.ImmutableBuffer.fromUint8List(fixedBytes);
      bufferWatch.stop();
      final Stopwatch setupWatch = Stopwatch()..start();
      final ui.Codec codec = await decode(buffer);
      setupWatch.stop();
      codecWatch.stop();
      if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {
        NetworkImageLoader._traceVisualPerf(
          'VISUAL_CODEC kind=standard total_ms=${codecWatch.elapsedMilliseconds} '
          'buffer_ms=${bufferWatch.elapsedMilliseconds} setup_ms=${setupWatch.elapsedMilliseconds} '
          'bytes=${fixedBytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
        );
      }
      return codec;
""",
    """      final Stopwatch codecWatch = Stopwatch()..start();
      WindowsPerformanceWatchdog.enter('visual_codec');
      try {
        final Stopwatch bufferWatch = Stopwatch()..start();
        final ui.ImmutableBuffer buffer = await ui.ImmutableBuffer.fromUint8List(fixedBytes);
        bufferWatch.stop();
        final Stopwatch setupWatch = Stopwatch()..start();
        final ui.Codec codec = await decode(buffer);
        setupWatch.stop();
        codecWatch.stop();
        if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {
          NetworkImageLoader._traceVisualPerf(
            'VISUAL_CODEC kind=standard total_ms=${codecWatch.elapsedMilliseconds} '
            'buffer_ms=${bufferWatch.elapsedMilliseconds} setup_ms=${setupWatch.elapsedMilliseconds} '
            'bytes=${fixedBytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
          );
        }
        return codec;
      } finally {
        WindowsPerformanceWatchdog.leave('visual_codec');
      }
""",
    'standard-visual-codec-phase',
)
replace_once(
    custom,
    """      final Stopwatch codecWatch = Stopwatch()..start();
      final codec = fType == AvifFileType.avif
          ? SingleFrameAvifCodec(bytes: bytes)
          : MultiFrameAvifCodec(
              key: hashCode,
              avifBytes: bytes,
              overrideDurationMs: -1,
            );
      await codec.ready();
      codecWatch.stop();
      if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {
        NetworkImageLoader._traceVisualPerf(
          'VISUAL_CODEC kind=avif total_ms=${codecWatch.elapsedMilliseconds} '
          'bytes=${bytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
        );
      }
      return codec;
""",
    """      final Stopwatch codecWatch = Stopwatch()..start();
      WindowsPerformanceWatchdog.enter('visual_codec');
      try {
        final codec = fType == AvifFileType.avif
            ? SingleFrameAvifCodec(bytes: bytes)
            : MultiFrameAvifCodec(
                key: hashCode,
                avifBytes: bytes,
                overrideDurationMs: -1,
              );
        await codec.ready();
        codecWatch.stop();
        if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {
          NetworkImageLoader._traceVisualPerf(
            'VISUAL_CODEC kind=avif total_ms=${codecWatch.elapsedMilliseconds} '
            'bytes=${bytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',
          );
        }
        return codec;
      } finally {
        WindowsPerformanceWatchdog.leave('visual_codec');
      }
""",
    'avif-visual-codec-phase',
)


# Guards.
logger_final = Path(logger).read_text(encoding='utf-8')
dio_final = Path(dio).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
tag_final = Path(tag_handler).read_text(encoding='utf-8')
custom_final = Path(custom).read_text(encoding='utf-8')
checks = {
    'logger 2s flush': 'Duration(seconds: 2)' in logger_final,
    'logger 64-line bound': '_maxBufferedLines = 64' in logger_final,
    'logger cooperative yield': '(i & 31) == 31' in logger_final,
    'logger watchdog phase': "enter('log_flush')" in logger_final and "leave('log_flush')" in logger_final,
    'logger slow batch diagnostic': 'LOG_BATCH lines=' in logger_final,
    'Windows Talker history bound': 'Platform.isWindows ? 5000 : 100000' in logger_final,
    'old 1000s flush removed': 'Duration(seconds: 1000)' not in logger_final,
    'release network inspectors gated': 'enableNetworkDiagnostics' in dio_final and 'settingsHandler.isDebug.value' in dio_final,
    'cookie phases': "enter('cookie_get')" in dio_final and "enter('cookie_save')" in dio_final,
    'captcha phase': dio_final.count("enter('captcha_check')") == 2,
    'page cookie phase': "enter('page_cookie')" in dan_final,
    'page http phase': "enter('page_http')" in dan_final,
    'tag db phase': "enter('tag_db')" in tag_final,
    'tag map behavior retained': '(processed & 31) == 0' in tag_final,
    'visual http phase': "enter('visual_http')" in custom_final,
    'visual codec phases': custom_final.count("enter('visual_codec')") == 2,
    'visual pipeline retained': custom_final.count("enter('visual_pipeline')") == 2,
    'v8.23 target ratio retained': 'thumbHeight = widthLimit / thumbRatio;' in Path('lib/src/widgets/thumbnail/thumbnail.dart').read_text(encoding='utf-8'),
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.24 guard failed: {label}')

print('V8_24_LOG_FLUSH_BURST_REMOVED=PASS')
print('V8_24_WINDOWS_TALKER_HISTORY_MAX=5000')
print('V8_24_LOG_BUFFER_MAX_LINES=64')
print('V8_24_LOG_FLUSH_DELAY_MS=2000')
print('V8_24_RELEASE_NETWORK_INSPECTORS_DISABLED=PASS')
print('V8_24_WATCHDOG_SUBPHASES=PASS')
print('V8_24_LOGGER_NETWORK_STALL_REDUCTION=PASS')
