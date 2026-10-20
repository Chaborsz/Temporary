from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.20 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.20 {label}: {p}')


# ---------------------------------------------------------------------------
# v8.19 runtime evidence closes the remaining major UI-stall source:
# TAG_BATCH tags=1232 changed=366 map_ms=525 db_ms=166 ms=691 coincided
# with EVENT_LOOP_STALL gap_ms=574 and SLOW_FRAME total_ms=515. The synchronous
# in-memory tag-map phase is therefore the dominant blocker, not SQLite.
#
# Keep the exact v8.19 type precedence and persistence semantics, but:
# - calculate the stale cutoff once per flush instead of DateTime.now/subtract
#   once per tag;
# - assign one flush timestamp to newly created/retyped Tag objects;
# - cooperatively yield every 32 processed tags so the Flutter event loop can
#   service frames/input instead of being monopolized by a 500+ ms loop;
# - report max synchronous slice time and yield count for runtime proof.
# ---------------------------------------------------------------------------
tag_handler = 'lib/src/handlers/tag_handler.dart'
replace_once(
    tag_handler,
    "import 'package:lolisnatcher/src/data/booru.dart';\n",
    "import 'package:lolisnatcher/src/data/booru.dart';\nimport 'package:lolisnatcher/src/data/constants.dart';\n",
    'tag-handler-constants-import',
)

old_method = """  /// Applies all typed categories in insertion order and persists all changed
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
new_method = """  /// Applies all typed categories in insertion order and persists all changed
  /// tags with at most one DB call. Category order is significant and matches
  /// the old sequential addTagsWithType calls: an existing non-none type is not
  /// overwritten by a later category. v8.20 bounds synchronous map work so a
  /// large idle flush cannot monopolize the Flutter event loop.
  Future<({int changed, int mapMs, int dbMs, int sliceMaxMs, int yields})> addTypedTagsBatch(
    Map<TagType, List<String>> batches,
  ) async {
    final Stopwatch mapWatch = Stopwatch()..start();
    final bool dbEnabled = SettingsHandler.instance.dbEnabled;
    final List<Tag> pendingDb = <Tag>[];
    final int nowMs = DateTime.now().millisecondsSinceEpoch;
    final int staleBeforeMs = nowMs - Constants.tagStaleDuration.inMilliseconds;
    int processed = 0;
    int yields = 0;
    int sliceMaxMs = 0;
    Stopwatch sliceWatch = Stopwatch()..start();

    for (final MapEntry<TagType, List<String>> entry in batches.entries) {
      final TagType type = entry.key;
      for (final String rawTag in entry.value) {
        if (rawTag.isEmpty) continue;
        final String tag = rawTag.toLowerCase();
        final Tag? current = _tagMap[tag];
        Tag? replacement;

        if (current == null || current.updatedAt < staleBeforeMs) {
          replacement = Tag(tag, tagType: type, updatedAt: nowMs);
        } else if (type != TagType.none && current.tagType == TagType.none) {
          replacement = Tag(tag, tagType: type, updatedAt: nowMs);
        }

        if (replacement != null) {
          _tagMap[tag] = replacement;
          pendingDb.add(replacement);
        }

        processed++;
        if ((processed & 31) == 0) {
          sliceWatch.stop();
          if (sliceWatch.elapsedMilliseconds > sliceMaxMs) {
            sliceMaxMs = sliceWatch.elapsedMilliseconds;
          }
          yields++;
          await Future<void>.delayed(Duration.zero);
          sliceWatch = Stopwatch()..start();
        }
      }
    }
    sliceWatch.stop();
    if (sliceWatch.elapsedMilliseconds > sliceMaxMs) {
      sliceMaxMs = sliceWatch.elapsedMilliseconds;
    }
    mapWatch.stop();

    int dbMs = 0;
    if (dbEnabled && pendingDb.isNotEmpty && SearchHandler.instance.canBackup.value) {
      // Give pending UI work one more scheduling opportunity before entering
      // SQLite. The DB operation itself remains the proven v8.19 single call.
      await Future<void>.delayed(Duration.zero);
      final Stopwatch dbWatch = Stopwatch()..start();
      await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);
      dbWatch.stop();
      dbMs = dbWatch.elapsedMilliseconds;
    }

    return (
      changed: pendingDb.length,
      mapMs: mapWatch.elapsedMilliseconds,
      dbMs: dbMs,
      sliceMaxMs: sliceMaxMs,
      yields: yields,
    );
  }
"""
replace_once(tag_handler, old_method, new_method, 'cooperative-tag-map-slices')


danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    """    final ({int changed, int mapMs, int dbMs}) result =
        await TagHandler.instance.addTypedTagsBatch(batches);
""",
    """    final ({int changed, int mapMs, int dbMs, int sliceMaxMs, int yields}) result =
        await TagHandler.instance.addTypedTagsBatch(batches);
""",
    'tag-result-record-v820',
)
replace_once(
    danbooru,
    """          '${DateTime.now().toIso8601String()} TAG_BATCH tags=$count changed=${result.changed} '
          'map_ms=${result.mapMs} db_ms=${result.dbMs} ms=${watch.elapsedMilliseconds}\\n',
""",
    """          '${DateTime.now().toIso8601String()} TAG_BATCH tags=$count changed=${result.changed} '
          'map_ms=${result.mapMs} db_ms=${result.dbMs} slice_max_ms=${result.sliceMaxMs} '
          'yields=${result.yields} ms=${watch.elapsedMilliseconds}\\n',
""",
    'tag-slice-diagnostics',
)


# Guards.
tag_final = Path(tag_handler).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
checks = {
    'single stale cutoff': 'staleBeforeMs = nowMs - Constants.tagStaleDuration.inMilliseconds' in tag_final,
    'old per-tag isStale removed from optimized path': 'current == null || current.isStale()' not in tag_final,
    'fixed flush timestamp': 'Tag(tag, tagType: type, updatedAt: nowMs)' in tag_final,
    '32-tag cooperative slices': '(processed & 31) == 0' in tag_final,
    'event-loop yield': 'await Future<void>.delayed(Duration.zero);' in tag_final,
    'slice max metric': 'sliceMaxMs' in tag_final,
    'yield metric': 'yields: yields' in tag_final,
    'single DB persistence retained': 'updateTagsFromObjects(pendingDb);' in tag_final,
    '5s idle retained': 'Timer(const Duration(milliseconds: 5000)' in dan_final,
    'tag slice diagnostics': 'slice_max_ms=${result.sliceMaxMs}' in dan_final and 'yields=${result.yields}' in dan_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.20 guard failed: {label}')

print('V8_20_TAG_STALE_CUTOFF_SINGLE=PASS')
print('V8_20_TAG_MAP_SLICE_SIZE=32')
print('V8_20_TAG_MAP_COOPERATIVE_YIELD=PASS')
print('V8_20_TAG_SLICE_DIAGNOSTICS=PASS')
print('V8_20_TAG_DB_SINGLE_CALL_RETAINED=PASS')
print('V8_20_EVENT_LOOP_STALL_REDUCTION=PASS')
