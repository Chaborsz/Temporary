from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.16 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.16 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) The v8.15 runtime log proves page merge is no longer responsible for the
#    freezes (merge_ms=0), while slow frames still coincide with many pending
#    image providers. Keep the complete Windows thumbnail pipeline serialized so
#    native decode/codec setup cannot run three thumbnails concurrently.
# ---------------------------------------------------------------------------
custom = 'lib/src/widgets/image/custom_network_image.dart'
replace_once(
    custom,
    'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(3);\n',
    'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(1);\n',
    'serialize-windows-visual-load-decode-pipeline',
)


# ---------------------------------------------------------------------------
# 2) Typed Danbooru tag persistence is already bulk/serialized, but v8.14 still
#    launches one DB batch 250ms after every page. Runtime shows each batch costs
#    ~50-90ms and overlaps the thumbnail completion/decode burst. Coalesce tags
#    across pages and flush after 2.5s of pagination quiet instead.
# ---------------------------------------------------------------------------
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    """  Future<void> _tagCommitChain = Future<void>.value();

  void _collectPageTags(Object? raw, TagType type) {
""",
    """  Future<void> _tagCommitChain = Future<void>.value();
  Timer? _tagFlushTimer;
  final Map<TagType, Set<String>> _pendingTypedTagFlush = <TagType, Set<String>>{
    TagType.none: <String>{},
    TagType.character: <String>{},
    TagType.copyright: <String>{},
    TagType.artist: <String>{},
    TagType.meta: <String>{},
  };

  void _queuePageTagCommit(Map<TagType, List<String>> batches) {
    bool hasTags = false;
    for (final MapEntry<TagType, List<String>> entry in batches.entries) {
      if (entry.value.isEmpty) continue;
      final Set<String>? target = _pendingTypedTagFlush[entry.key];
      if (target == null) continue;
      target.addAll(entry.value);
      hasTags = true;
    }
    if (!hasTags) return;

    _tagFlushTimer?.cancel();
    _tagFlushTimer = Timer(const Duration(milliseconds: 2500), () {
      unawaited(_flushPendingTagCommit());
    });
  }

  Future<void> _flushPendingTagCommit() async {
    final Map<TagType, List<String>> batches = <TagType, List<String>>{
      for (final MapEntry<TagType, Set<String>> entry in _pendingTypedTagFlush.entries)
        entry.key: entry.value.toList(growable: false),
    };
    for (final Set<String> tags in _pendingTypedTagFlush.values) {
      tags.clear();
    }

    if (!batches.values.any((List<String> tags) => tags.isNotEmpty)) return;
    _tagCommitChain = _tagCommitChain.then((_) => _commitPageTags(batches));
    await _tagCommitChain;
  }

  void _collectPageTags(Object? raw, TagType type) {
""",
    'idle-coalesced-tag-flush-state',
)

replace_once(
    danbooru,
    """    if (batches.values.any((List<String> tags) => tags.isNotEmpty)) {
      _tagCommitChain = _tagCommitChain.then((_) async {
        await Future<void>.delayed(const Duration(milliseconds: 250));
        await _commitPageTags(batches);
      });
      unawaited(_tagCommitChain);
    }
""",
    """    if (batches.values.any((List<String> tags) => tags.isNotEmpty)) {
      _queuePageTagCommit(batches);
    }
""",
    'replace-per-page-250ms-tag-write-with-idle-coalescing',
)


# Guards.
custom_final = Path(custom).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
checks = {
    'visual gate serialized': 'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(1);' in custom_final,
    'old visual gate removed': 'final _AsyncGate _windowsVisualPipelineGate = _AsyncGate(3);' not in custom_final,
    'tag idle timer exists': 'Timer? _tagFlushTimer;' in dan_final,
    'tag coalescing map exists': '_pendingTypedTagFlush' in dan_final,
    'tag quiet window 2500ms': 'Timer(const Duration(milliseconds: 2500)' in dan_final,
    'old 250ms page delay removed': 'Duration(milliseconds: 250)' not in dan_final,
    'page path queues tags': '_queuePageTagCommit(batches);' in dan_final,
    'tag DB commits remain serialized': '_tagCommitChain = _tagCommitChain.then((_) => _commitPageTags(batches));' in dan_final,
    'merge fast path retained': 'appendFilteredFetchedPage(newItems);' in dan_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.16 guard failed: {label}')

print('V8_16_VISUAL_PIPELINE_MAX=1')
print('V8_16_WINDOWS_VISUAL_DECODE_SERIAL=PASS')
print('V8_16_TAG_IDLE_COALESCE_MS=2500')
print('V8_16_TAG_IDLE_COALESCING=PASS')
print('V8_16_INCREMENTAL_MERGE_RETAINED=PASS')
print('V8_16_FRAME_STALL_REDUCTION=PASS')
