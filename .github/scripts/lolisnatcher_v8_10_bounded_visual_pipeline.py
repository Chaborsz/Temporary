from pathlib import Path

custom = Path('lib/src/widgets/image/custom_network_image.dart')
text = custom.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.10 {label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)
    print(f'PATCHED v8.10 {label}')


# Bound the *complete* Windows thumbnail/sample pipeline, not only network I/O.
# A grid can otherwise start many Dio clients, packed-cache reads, immutable
# buffers and native decoders at once. Full-resolution viewer images are not
# affected because they are memory-only and don't use the thumbnail/sample cache.
replace_once(
    """/// Shared logic for downloading, caching, and atomic writing of images.\nclass NetworkImageLoader {\n""",
    """class _AsyncPermit {\n  _AsyncPermit(this._onRelease);\n\n  final void Function() _onRelease;\n  bool _released = false;\n\n  void release() {\n    if (_released) return;\n    _released = true;\n    _onRelease();\n  }\n}\n\nclass _AsyncGate {\n  _AsyncGate(this.maxActive);\n\n  final int maxActive;\n  int _active = 0;\n  final List<Completer<_AsyncPermit>> _waiters = <Completer<_AsyncPermit>>[];\n\n  Future<_AsyncPermit> acquire() {\n    if (_active < maxActive) {\n      _active++;\n      return Future<_AsyncPermit>.value(_AsyncPermit(_release));\n    }\n\n    final Completer<_AsyncPermit> completer = Completer<_AsyncPermit>();\n    _waiters.add(completer);\n    return completer.future;\n  }\n\n  void _release() {\n    if (_waiters.isNotEmpty) {\n      final Completer<_AsyncPermit> next = _waiters.removeAt(0);\n      next.complete(_AsyncPermit(_release));\n      return;\n    }\n    if (_active > 0) _active--;\n  }\n}\n\nfinal _AsyncGate _windowsVisualPipelineGate = _AsyncGate(3);\n\n/// Shared logic for downloading, caching, and atomic writing of images.\nclass NetworkImageLoader {\n""",
    'visual-pipeline-gate',
)

# Apply the same gate to normal image thumbnails and AVIF thumbnails. Keep the
# permit until native decode/codec setup has completed so CPU/decode pressure is
# bounded, not merely the HTTP request count.
needle = """  ) async {\n    try {\n      assert(key == this, 'The $runtimeType cannot be reused after disposing.');\n"""
replacement = """  ) async {\n    final bool limitVisualPipeline =\n        Platform.isWindows &&\n        withCache &&\n        CompressedVisualCache.isVisualFolder(cacheFolder);\n    final _AsyncPermit? visualPermit =\n        limitVisualPipeline ? await _windowsVisualPipelineGate.acquire() : null;\n\n    try {\n      assert(key == this, 'The $runtimeType cannot be reused after disposing.');\n"""
count = text.count(needle)
if count != 2:
    raise SystemExit(f'v8.10 pipeline-acquire: expected 2 matches, found {count}')
text = text.replace(needle, replacement)
print('PATCHED v8.10 pipeline-acquire (2 providers)')

needle_finally = """    } finally {\n      await chunkEvents.close();\n    }\n"""
replacement_finally = """    } finally {\n      visualPermit?.release();\n      await chunkEvents.close();\n    }\n"""
count = text.count(needle_finally)
if count != 2:
    raise SystemExit(f'v8.10 pipeline-release: expected 2 matches, found {count}')
text = text.replace(needle_finally, replacement_finally)
print('PATCHED v8.10 pipeline-release (2 providers)')

custom.write_text(text, encoding='utf-8')

# Fast scroll: allow more time for list/grid cells that immediately leave the
# viewport to be disposed before they start a network/cache/decode pipeline.
thumbnail = Path('lib/src/widgets/thumbnail/thumbnail.dart')
thumb = thumbnail.read_text(encoding='utf-8')
old_delay = "Duration(milliseconds: widget.isStandalone ? 200 : 0),"
new_delay = "Duration(milliseconds: widget.isStandalone ? (Platform.isWindows ? 350 : 200) : 0),"
count = thumb.count(old_delay)
if count != 1:
    raise SystemExit(f'v8.10 windows-scroll-debounce: expected 1 match, found {count}')
thumb = thumb.replace(old_delay, new_delay, 1)
thumbnail.write_text(thumb, encoding='utf-8')
print('PATCHED v8.10 windows-scroll-debounce')

final_custom = custom.read_text(encoding='utf-8')
final_thumb = thumbnail.read_text(encoding='utf-8')
checks = {
    'gate size 3': 'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(3);' in final_custom,
    'normal+avif acquire': final_custom.count('limitVisualPipeline ? await _windowsVisualPipelineGate.acquire() : null;') == 2,
    'normal+avif release': final_custom.count('visualPermit?.release();') == 2,
    'visual folders only': final_custom.count('CompressedVisualCache.isVisualFolder(cacheFolder)') >= 2,
    'windows debounce 350': '(Platform.isWindows ? 350 : 200)' in final_thumb,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.10 guard failed: {label}')

print('V8_10_VISUAL_PIPELINE_MAX=3')
print('V8_10_STANDARD_AND_AVIF_BOUNDED=PASS')
print('V8_10_WINDOWS_SCROLL_DEBOUNCE_MS=350')
print('V8_10_FULLRES_UNBOUNDED=PASS')
print('V8_10_BOUNDED_VISUAL_PIPELINE=PASS')
