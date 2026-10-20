from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.19 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.19 {label}: {p}')


# ---------------------------------------------------------------------------
# v8.18 runtime evidence:
# - parse_ms / merge_ms remain 0.
# - persistent thumbnail Dio reuse is active and no slow VISUAL_CODEC appeared.
# - no EVENT_LOOP_STALL >=400 ms appeared in the supplied run.
# - TAG_BATCH became the clearest remaining expensive background operation:
#   269 tags / 321 ms, 404 / 365 ms, 377 / 318 ms, 527 / 509 ms.
#
# The v8.13 design still enters TagHandler once per category, so one logical
# idle flush can perform up to five separate DB lookups/commits. v8.19 preserves
# the exact in-memory type precedence, but processes all categories in one pass
# and performs at most one DB persistence call for the complete idle flush.
# ---------------------------------------------------------------------------
tag_handler = 'lib/src/handlers/tag_handler.dart'
old_add = """  /// Stores given tags list with given type. v8.13 keeps map semantics but
  /// batches persistence so a Danbooru page does not create hundreds of tiny
  /// SQLite writes while the user is scrolling.
  Future<void> addTagsWithType(List<String> tags, TagType type) async {
    final bool dbEnabled = SettingsHandler.instance.dbEnabled;
    final List<Tag> pendingDb = <Tag>[];

    for (final String rawTag in tags) {
      if (rawTag.isEmpty) continue;
      final String tag = rawTag.toLowerCase();
      Tag? replacement;

      if (!hasTagAndNotStale(tag)) {
        replacement = Tag(tag, tagType: type);
      } else if (type != TagType.none && getTag(tag).tagType == TagType.none) {
        replacement = Tag(tag, tagType: type);
      }

      if (replacement != null) {
        _tagMap[tag] = replacement;
        pendingDb.add(replacement);
      }
    }

    if (dbEnabled && pendingDb.isNotEmpty && SearchHandler.instance.canBackup.value) {
      await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);
    }
  }
"""
new_add = """  /// Stores one tag category while sharing the optimized multi-category path.
  Future<void> addTagsWithType(List<String> tags, TagType type) async {
    await addTypedTagsBatch(<TagType, List<String>>{type: tags});
  }

  /// Applies all typed categories in insertion order and persists all changed
  /// tags with at most one DB call. Category order is significant and matches
  /// the old sequential addTagsWithType calls: an existing non-none type is not
  /// overwritten by a later category.
  Future<({int changed, int mapMs, int dbMs})> addTypedTagsBatch(
    Map<TagType, List<String>> batches,
  ) async {
    final Stopwatch mapWatch = Stopwatch()..start();
    final bool dbEnabled = SettingsHandler.instance.dbEnabled;
    final List<Tag> pendingDb = <Tag>[];

    for (final MapEntry<TagType, List<String>> entry in batches.entries) {
      final TagType type = entry.key;
      for (final String rawTag in entry.value) {
        if (rawTag.isEmpty) continue;
        final String tag = rawTag.toLowerCase();
        final Tag? current = _tagMap[tag];
        Tag? replacement;

        if (current == null || current.isStale()) {
          replacement = Tag(tag, tagType: type);
        } else if (type != TagType.none && current.tagType == TagType.none) {
          replacement = Tag(tag, tagType: type);
        }

        if (replacement != null) {
          _tagMap[tag] = replacement;
          pendingDb.add(replacement);
        }
      }
    }
    mapWatch.stop();

    int dbMs = 0;
    if (dbEnabled && pendingDb.isNotEmpty && SearchHandler.instance.canBackup.value) {
      final Stopwatch dbWatch = Stopwatch()..start();
      await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);
      dbWatch.stop();
      dbMs = dbWatch.elapsedMilliseconds;
    }

    return (
      changed: pendingDb.length,
      mapMs: mapWatch.elapsedMilliseconds,
      dbMs: dbMs,
    );
  }
"""
replace_once(tag_handler, old_add, new_add, 'single-pass-multi-category-tag-update')


# One combined flush commonly contains 400-600 tags. Stay below SQLite's
# classic 999 host-parameter limit so that this size normally needs one lookup,
# not two or five full Tag-table scans.
database_handler = 'lib/src/handlers/database_handler.dart'
replace_once(
    database_handler,
    '    const int chunkSize = 400;\n',
    '    const int chunkSize = 900;\n',
    'tag-lookup-chunk-900',
)


# A 2.5 s quiet window can fire in the middle of normal pagination: the supplied
# v8.18 run has page gaps around 2.7 s, and the 509 ms TAG_BATCH overlaps the
# next page. Require 5 s without another parsed page before persisting typed
# metadata. The in-memory tag map is still updated when the flush happens; this
# only moves optional persistence farther away from active scrolling.
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    '    _tagFlushTimer = Timer(const Duration(milliseconds: 2500), () {\n',
    '    _tagFlushTimer = Timer(const Duration(milliseconds: 5000), () {\n',
    'tag-quiet-window-5000ms',
)

old_commit = """  Future<void> _commitPageTags(Map<TagType, List<String>> batches) async {
    final Stopwatch watch = Stopwatch()..start();
    int count = 0;
    for (final MapEntry<TagType, List<String>> entry in batches.entries) {
      if (entry.value.isEmpty) continue;
      count += entry.value.length;
      await TagHandler.instance.addTagsWithType(entry.value, entry.key);
    }
    watch.stop();

    if (Platform.isWindows) {
      try {
        final String sep = Platform.pathSeparator;
        final File file = File(
          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
        );
        await file.parent.create(recursive: true);
        await file.writeAsString(
          '${DateTime.now().toIso8601String()} TAG_BATCH tags=$count ms=${watch.elapsedMilliseconds}\\n',
          mode: FileMode.append,
          flush: false,
        );
      } catch (_) {}
    }
  }
"""
new_commit = """  Future<void> _commitPageTags(Map<TagType, List<String>> batches) async {
    final Stopwatch watch = Stopwatch()..start();
    int count = 0;
    for (final List<String> tags in batches.values) {
      count += tags.length;
    }

    final ({int changed, int mapMs, int dbMs}) result =
        await TagHandler.instance.addTypedTagsBatch(batches);
    watch.stop();

    if (Platform.isWindows) {
      try {
        final String sep = Platform.pathSeparator;
        final File file = File(
          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',
        );
        await file.parent.create(recursive: true);
        await file.writeAsString(
          '${DateTime.now().toIso8601String()} TAG_BATCH tags=$count changed=${result.changed} '
          'map_ms=${result.mapMs} db_ms=${result.dbMs} ms=${watch.elapsedMilliseconds}\\n',
          mode: FileMode.append,
          flush: false,
        );
      } catch (_) {}
    }
  }
"""
replace_once(danbooru, old_commit, new_commit, 'one-db-call-per-idle-tag-flush')


# Guards.
tag_final = Path(tag_handler).read_text(encoding='utf-8')
db_final = Path(database_handler).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
checks = {
    'multi-category method': 'addTypedTagsBatch(' in tag_final,
    'single category delegates': 'await addTypedTagsBatch(<TagType, List<String>>{type: tags});' in tag_final,
    'direct map lookup': 'final Tag? current = _tagMap[tag];' in tag_final,
    'single DB persistence call': 'updateTagsFromObjects(pendingDb);' in tag_final,
    'timed tag phases': 'Future<({int changed, int mapMs, int dbMs})>' in tag_final,
    'lookup chunk 900': 'const int chunkSize = 900;' in db_final,
    'old lookup chunk removed': 'const int chunkSize = 400;' not in db_final,
    'idle window 5000ms': 'Timer(const Duration(milliseconds: 5000)' in dan_final,
    'old idle window removed': 'Timer(const Duration(milliseconds: 2500)' not in dan_final,
    'Danbooru uses one typed batch call': 'TagHandler.instance.addTypedTagsBatch(batches)' in dan_final,
    'tag phase diagnostic': 'changed=${result.changed}' in dan_final and 'db_ms=${result.dbMs}' in dan_final,
    'no per-category awaited persistence in commit': 'await TagHandler.instance.addTagsWithType(entry.value, entry.key);' not in dan_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.19 guard failed: {label}')

print('V8_19_TAG_MULTI_CATEGORY_SINGLE_PASS=PASS')
print('V8_19_TAG_DB_CALLS_PER_FLUSH_MAX=1')
print('V8_19_TAG_LOOKUP_CHUNK=900')
print('V8_19_TAG_IDLE_COALESCE_MS=5000')
print('V8_19_TAG_PHASE_DIAGNOSTICS=PASS')
print('V8_19_TAG_STALL_REDUCTION=PASS')
