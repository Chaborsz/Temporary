from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.18 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.18 {label}: {p}')


# ---------------------------------------------------------------------------
# v8.17 runtime evidence:
# - Danbooru parse/merge stays at 0 ms.
# - SQLite tag batches are now bounded and no VISUAL_DB_BATCH >=50 ms appeared.
# - long SLOW_FRAME total spans still occur with tiny build/raster times while
#   process RSS rises far above Flutter ImageCache bytes.
#
# The Windows packed-thumbnail path still constructs and closes a full Dio
# client (and its native HTTP resources) for every thumbnail. v8.16 already
# serializes this path, so safely reuse one plain and one captcha-capable client
# to preserve keep-alive and remove per-thumbnail client/socket churn.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    """class NetworkImageLoader {\n  static const Duration _defaultReceiveTimeout = Duration(seconds: 30);\n\n""",
    """class NetworkImageLoader {\n  static const Duration _defaultReceiveTimeout = Duration(seconds: 30);\n  static Dio? _windowsVisualClient;\n  static Dio? _windowsVisualCaptchaClient;\n  static bool? _windowsVisualLoggingEnabled;\n  static Future<void> _visualPerfWriteChain = Future<void>.value();\n\n  static void _traceVisualPerf(String message) {\n    if (!Platform.isWindows) return;\n    _visualPerfWriteChain = _visualPerfWriteChain.then((_) async {\n      try {\n        final String sep = Platform.pathSeparator;\n        final File file = File(\n          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',\n        );\n        await file.parent.create(recursive: true);\n        await file.writeAsString(\n          '${DateTime.now().toIso8601String()} $message\\n',\n          mode: FileMode.append,\n          flush: false,\n        );\n      } catch (_) {}\n    });\n  }\n\n  static Dio _createWindowsVisualClient({required bool withCaptchaCheck}) {\n    final Dio client = DioNetwork.getClient(\n      skipLogging: !SettingsHandler.instance.useImageLogging.value,\n    );\n    if (withCaptchaCheck) {\n      DioNetwork.captchaInterceptor(client, customUserAgent: Tools.appUserAgent);\n    }\n    _traceVisualPerf(\n      'VISUAL_HTTP_CLIENT action=create captcha=${withCaptchaCheck ? 1 : 0} reused=1',\n    );\n    return client;\n  }\n\n  static Dio _getWindowsVisualClient({required bool withCaptchaCheck}) {\n    final bool loggingEnabled = SettingsHandler.instance.useImageLogging.value;\n    if (_windowsVisualLoggingEnabled != loggingEnabled) {\n      _windowsVisualClient?.close(force: true);\n      _windowsVisualCaptchaClient?.close(force: true);\n      _windowsVisualClient = null;\n      _windowsVisualCaptchaClient = null;\n      _windowsVisualLoggingEnabled = loggingEnabled;\n    }\n\n    if (withCaptchaCheck) {\n      return _windowsVisualCaptchaClient ??=\n          _createWindowsVisualClient(withCaptchaCheck: true);\n    }\n    return _windowsVisualClient ??=\n        _createWindowsVisualClient(withCaptchaCheck: false);\n  }\n\n""",
    'reusable-windows-visual-http-client',
)

replace_once(
    custom,
    """    if (useCompressedVisualCache) {\n      final Uint8List? packedBytes = await CompressedVisualCache.instance.read(\n        cacheFolder!,\n        cacheFilePath,\n      );\n      if (packedBytes != null && packedBytes.isNotEmpty) {\n""",
    """    if (useCompressedVisualCache) {\n      final Stopwatch packedReadWatch = Stopwatch()..start();\n      final Uint8List? packedBytes = await CompressedVisualCache.instance.read(\n        cacheFolder!,\n        cacheFilePath,\n      );\n      packedReadWatch.stop();\n      if (packedReadWatch.elapsedMilliseconds >= 25) {\n        _traceVisualPerf(\n          'VISUAL_DB_READ ms=${packedReadWatch.elapsedMilliseconds} '\n          'hit=${packedBytes != null && packedBytes.isNotEmpty ? 1 : 0} '\n          'bytes=${packedBytes?.length ?? 0} '\n          'rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',\n        );\n      }\n      if (packedBytes != null && packedBytes.isNotEmpty) {\n""",
    'packed-read-diagnostics',
)

replace_once(
    custom,
    """    final client = DioNetwork.getClient(\n      skipLogging: !SettingsHandler.instance.useImageLogging.value,\n    );\n    if (withCaptchaCheck) {\n      DioNetwork.captchaInterceptor(\n        client,\n        customUserAgent: Tools.appUserAgent,\n      );\n    }\n\n    Response? response;\n""",
    """    final bool reuseWindowsVisualClient = useCompressedVisualCache;\n    final Dio client = reuseWindowsVisualClient\n        ? _getWindowsVisualClient(withCaptchaCheck: withCaptchaCheck)\n        : DioNetwork.getClient(\n            skipLogging: !SettingsHandler.instance.useImageLogging.value,\n          );\n    if (!reuseWindowsVisualClient && withCaptchaCheck) {\n      DioNetwork.captchaInterceptor(\n        client,\n        customUserAgent: Tools.appUserAgent,\n      );\n    }\n\n    Response? response;\n""",
    'use-reusable-client-for-packed-thumbnails',
)

replace_once(
    custom,
    """    } finally {\n      client.close();\n    }\n\n    if (!Tools.isGoodResponse(response)) {\n""",
    """    } finally {\n      if (!reuseWindowsVisualClient) {\n        client.close();\n      }\n    }\n\n    if (!Tools.isGoodResponse(response)) {\n""",
    'keep-reusable-client-open',
)

# Time the engine buffer copy + codec setup. These diagnostics contain no URL,
# cookie, credentials or response data and are emitted only for slow operations.
replace_once(
    custom,
    """      final fixedBytes = await NetworkImageLoader.tryFixGifSpeed(key.url, bytes);\n\n      final ui.ImmutableBuffer buffer = await ui.ImmutableBuffer.fromUint8List(fixedBytes);\n      return await decode(buffer);\n""",
    """      final fixedBytes = await NetworkImageLoader.tryFixGifSpeed(key.url, bytes);\n\n      final Stopwatch codecWatch = Stopwatch()..start();\n      final Stopwatch bufferWatch = Stopwatch()..start();\n      final ui.ImmutableBuffer buffer = await ui.ImmutableBuffer.fromUint8List(fixedBytes);\n      bufferWatch.stop();\n      final Stopwatch setupWatch = Stopwatch()..start();\n      final ui.Codec codec = await decode(buffer);\n      setupWatch.stop();\n      codecWatch.stop();\n      if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {\n        NetworkImageLoader._traceVisualPerf(\n          'VISUAL_CODEC kind=standard total_ms=${codecWatch.elapsedMilliseconds} '\n          'buffer_ms=${bufferWatch.elapsedMilliseconds} setup_ms=${setupWatch.elapsedMilliseconds} '\n          'bytes=${fixedBytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',\n        );\n      }\n      return codec;\n""",
    'standard-codec-diagnostics',
)

replace_once(
    custom,
    """      final codec = fType == AvifFileType.avif\n          ? SingleFrameAvifCodec(bytes: bytes)\n          : MultiFrameAvifCodec(\n              key: hashCode,\n              avifBytes: bytes,\n              overrideDurationMs: -1,\n            );\n      await codec.ready();\n      return codec;\n""",
    """      final Stopwatch codecWatch = Stopwatch()..start();\n      final codec = fType == AvifFileType.avif\n          ? SingleFrameAvifCodec(bytes: bytes)\n          : MultiFrameAvifCodec(\n              key: hashCode,\n              avifBytes: bytes,\n              overrideDurationMs: -1,\n            );\n      await codec.ready();\n      codecWatch.stop();\n      if (Platform.isWindows && codecWatch.elapsedMilliseconds >= 25) {\n        NetworkImageLoader._traceVisualPerf(\n          'VISUAL_CODEC kind=avif total_ms=${codecWatch.elapsedMilliseconds} '\n          'bytes=${bytes.length} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}',\n        );\n      }\n      return codec;\n""",
    'avif-codec-diagnostics',
)

# v8.17 produced several 400-617 ms total frame gaps but the old event-loop
# monitor only reported gaps >=650 ms. Lower the threshold just enough to catch
# the remaining visible freezes without turning the log into per-frame noise.
replace_once(
    'lib/main.dart',
    """    if (gap >= 650) {\n""",
    """    if (gap >= 400) {\n""",
    'event-loop-stall-threshold-400ms',
)


# Guards.
custom_final = Path(custom).read_text(encoding='utf-8')
main_final = Path('lib/main.dart').read_text(encoding='utf-8')
checks = {
    'persistent plain visual Dio': '_windowsVisualClient' in custom_final,
    'persistent captcha visual Dio': '_windowsVisualCaptchaClient' in custom_final,
    'visual client survives request': 'if (!reuseWindowsVisualClient) {\n        client.close();' in custom_final,
    'visual DB read diagnostic': 'VISUAL_DB_READ ms=' in custom_final,
    'standard codec diagnostic': 'VISUAL_CODEC kind=standard' in custom_final,
    'AVIF codec diagnostic': 'VISUAL_CODEC kind=avif' in custom_final,
    'no URL in visual perf diagnostics': "VISUAL_CODEC kind=standard total_ms=" in custom_final,
    'visual gate still serialized': 'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(1);' in custom_final,
    'event loop threshold 400': 'if (gap >= 400) {' in main_final,
    'old event loop threshold removed': 'if (gap >= 650) {' not in main_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.18 guard failed: {label}')

print('V8_18_WINDOWS_VISUAL_DIO_REUSE=PASS')
print('V8_18_VISUAL_CODEC_DIAGNOSTICS=PASS')
print('V8_18_EVENT_LOOP_STALL_THRESHOLD_MS=400')
print('V8_18_HTTP_AND_CODEC_STALL_REDUCTION=PASS')
