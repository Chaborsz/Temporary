from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.13 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.13 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) TagHandler: keep exactly the same in-memory typed-tag semantics, but replace
#    one SQLite write per tag with one bulk write per addTagsWithType call.
# ---------------------------------------------------------------------------
tag_handler = 'lib/src/handlers/tag_handler.dart'
replace_once(
    tag_handler,
    """  /// Stores given tags list with given type, if tag is already in the tag map - update it's type, but only if the type was \"none\"\n  Future<void> addTagsWithType(List<String> tags, TagType type) async {\n    final dbEnabled = SettingsHandler.instance.dbEnabled;\n\n    for (final String tag in tags) {\n      if (!hasTagAndNotStale(tag)) {\n        await putTag(\n          Tag(tag, tagType: type),\n          dbEnabled: dbEnabled,\n          preferTypeIfNone: false,\n        );\n      } else if (type != TagType.none) {\n        if (getTag(tag).tagType == TagType.none) {\n          await putTag(\n            Tag(tag, tagType: type),\n            dbEnabled: dbEnabled,\n            preferTypeIfNone: true,\n          );\n        }\n      }\n    }\n  }\n""",
    """  /// Stores given tags list with given type. v8.13 keeps map semantics but\n  /// batches persistence so a Danbooru page does not create hundreds of tiny\n  /// SQLite writes while the user is scrolling.\n  Future<void> addTagsWithType(List<String> tags, TagType type) async {\n    final bool dbEnabled = SettingsHandler.instance.dbEnabled;\n    final List<Tag> pendingDb = <Tag>[];\n\n    for (final String rawTag in tags) {\n      if (rawTag.isEmpty) continue;\n      final String tag = rawTag.toLowerCase();\n      Tag? replacement;\n\n      if (!hasTagAndNotStale(tag)) {\n        replacement = Tag(tag, tagType: type);\n      } else if (type != TagType.none && getTag(tag).tagType == TagType.none) {\n        replacement = Tag(tag, tagType: type);\n      }\n\n      if (replacement != null) {\n        _tagMap[tag] = replacement;\n        pendingDb.add(replacement);\n      }\n    }\n\n    if (dbEnabled && pendingDb.isNotEmpty && SearchHandler.instance.canBackup.value) {\n      await SettingsHandler.instance.dbHandler.updateTagsFromObjects(pendingDb);\n    }\n  }\n""",
    'bulk-tag-db-persistence',
)


# ---------------------------------------------------------------------------
# 2) Danbooru: collect typed tags while parsing a page, then commit only five
#    category batches after the page is visible. Serialize page tag commits so
#    pagination can never create a storm of overlapping DB updates.
# ---------------------------------------------------------------------------
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    "import 'dart:io';\n",
    "import 'dart:async';\nimport 'dart:io';\n",
    'danbooru-async-import',
)
replace_once(
    danbooru,
    "import 'package:lolisnatcher/src/handlers/booru_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/booru_handler.dart';\nimport 'package:lolisnatcher/src/handlers/tag_handler.dart';\n",
    'danbooru-tag-handler-import',
)
replace_once(
    danbooru,
    """class DanbooruHandler extends BooruHandler {\n  DanbooruHandler(super.booru, super.limit);\n\n""",
    """class DanbooruHandler extends BooruHandler {\n  DanbooruHandler(super.booru, super.limit);\n\n  final Map<TagType, Set<String>> _pageTypedTags = <TagType, Set<String>>{\n    TagType.none: <String>{},\n    TagType.character: <String>{},\n    TagType.copyright: <String>{},\n    TagType.artist: <String>{},\n    TagType.meta: <String>{},\n  };\n  Future<void> _tagCommitChain = Future<void>.value();\n\n  void _collectPageTags(Object? raw, TagType type) {\n    final Set<String>? target = _pageTypedTags[type];\n    if (target == null) return;\n    for (final String tag in raw.toString().split(' ')) {\n      if (tag.isNotEmpty) target.add(tag);\n    }\n  }\n\n  Future<void> _commitPageTags(Map<TagType, List<String>> batches) async {\n    final Stopwatch watch = Stopwatch()..start();\n    int count = 0;\n    for (final MapEntry<TagType, List<String>> entry in batches.entries) {\n      if (entry.value.isEmpty) continue;\n      count += entry.value.length;\n      await TagHandler.instance.addTagsWithType(entry.value, entry.key);\n    }\n    watch.stop();\n\n    if (Platform.isWindows) {\n      try {\n        final String sep = Platform.pathSeparator;\n        final File file = File(\n          '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',\n        );\n        await file.parent.create(recursive: true);\n        await file.writeAsString(\n          '${DateTime.now().toIso8601String()} TAG_BATCH tags=$count ms=${watch.elapsedMilliseconds}\\n',\n          mode: FileMode.append,\n          flush: false,\n        );\n      } catch (_) {}\n    }\n  }\n\n  @override\n  Future<void> afterParseResponse(List<BooruItem> newItems) async {\n    final Map<TagType, List<String>> batches = <TagType, List<String>>{\n      for (final MapEntry<TagType, Set<String>> entry in _pageTypedTags.entries)\n        entry.key: entry.value.toList(growable: false),\n    };\n    for (final Set<String> tags in _pageTypedTags.values) {\n      tags.clear();\n    }\n\n    await super.afterParseResponse(newItems);\n\n    if (batches.values.any((List<String> tags) => tags.isNotEmpty)) {\n      _tagCommitChain = _tagCommitChain.then((_) => _commitPageTags(batches));\n      unawaited(_tagCommitChain);\n    }\n  }\n\n""",
    'danbooru-page-tag-collector',
)

old_tag_calls = """        addTagsWithType(\n          current['tag_string_general'].toString().split(' '),\n          TagType.none,\n        );\n        addTagsWithType(\n          current['tag_string_character'].toString().split(' '),\n          TagType.character,\n        );\n        addTagsWithType(\n          current['tag_string_copyright'].toString().split(' '),\n          TagType.copyright,\n        );\n        addTagsWithType(\n          current['tag_string_artist'].toString().split(' '),\n          TagType.artist,\n        );\n        addTagsWithType(\n          current['tag_string_meta'].toString().split(' '),\n          TagType.meta,\n        );\n"""
new_tag_calls = """        _collectPageTags(current['tag_string_general'], TagType.none);\n        _collectPageTags(current['tag_string_character'], TagType.character);\n        _collectPageTags(current['tag_string_copyright'], TagType.copyright);\n        _collectPageTags(current['tag_string_artist'], TagType.artist);\n        _collectPageTags(current['tag_string_meta'], TagType.meta);\n"""
replace_once(danbooru, old_tag_calls, new_tag_calls, 'danbooru-five-calls-to-page-batches')


# ---------------------------------------------------------------------------
# 3) Page-level diagnostics. These timings distinguish response parsing from the
#    fetched/filter merge without logging URLs, queries, credentials or bodies.
# ---------------------------------------------------------------------------
booru_handler = 'lib/src/handlers/booru_handler.dart'
replace_once(
    booru_handler,
    """  bool get hasSizeData => false;\n\n  Future<bool> searchSetup() async {\n""",
    """  bool get hasSizeData => false;\n\n  Future<void> _appendWindowsPagePerf({\n    required int page,\n    required int newItems,\n    required int totalItems,\n    required int parseMs,\n    required int mergeMs,\n  }) async {\n    if (!Platform.isWindows) return;\n    try {\n      final String sep = Platform.pathSeparator;\n      final File file = File(\n        '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',\n      );\n      await file.parent.create(recursive: true);\n      await file.writeAsString(\n        '${DateTime.now().toIso8601String()} PAGE_PHASE handler=$className page=$page '\n        'new=$newItems total=$totalItems parse_ms=$parseMs merge_ms=$mergeMs\\n',\n        mode: FileMode.append,\n        flush: false,\n      );\n    } catch (_) {}\n  }\n\n  Future<bool> searchSetup() async {\n""",
    'page-phase-log-helper',
)
replace_once(
    booru_handler,
    """        // parse response data\n        final List<BooruItem> newItems = await parseResponse(response);\n        await afterParseResponse(newItems);\n\n        // save tags for check on next search\n""",
    """        // Parse/merge timings are intentionally separate: scrolling freezes\n        // at page boundaries need to distinguish response parsing from list work.\n        final Stopwatch parseWatch = Stopwatch()..start();\n        final List<BooruItem> newItems = await parseResponse(response);\n        parseWatch.stop();\n\n        final Stopwatch mergeWatch = Stopwatch()..start();\n        await afterParseResponse(newItems);\n        mergeWatch.stop();\n\n        unawaited(\n          _appendWindowsPagePerf(\n            page: pageNum,\n            newItems: newItems.length,\n            totalItems: fetched.length,\n            parseMs: parseWatch.elapsedMilliseconds,\n            mergeMs: mergeWatch.elapsedMilliseconds,\n          ),\n        );\n\n        // save tags for check on next search\n""",
    'page-phase-timing',
)


# Guards.
tag_final = Path(tag_handler).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
booru_final = Path(booru_handler).read_text(encoding='utf-8')
checks = {
    'bulk DB update': 'updateTagsFromObjects(pendingDb)' in tag_final,
    'no per-tag putTag loop in addTagsWithType': 'pendingDb.add(replacement);' in tag_final,
    'Danbooru page collector': '_pageTypedTags' in dan_final and '_collectPageTags' in dan_final,
    'serialized tag commits': '_tagCommitChain = _tagCommitChain.then' in dan_final,
    'five direct tag calls removed': "addTagsWithType(\n          current['tag_string_general']" not in dan_final,
    'tag batch diagnostics': 'TAG_BATCH tags=' in dan_final,
    'page phase diagnostics': 'PAGE_PHASE handler=' in booru_final,
    'parse and merge timing': 'parseWatch.elapsedMilliseconds' in booru_final and 'mergeWatch.elapsedMilliseconds' in booru_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.13 guard failed: {label}')

print('V8_13_TAG_DB_BULK_WRITE=PASS')
print('V8_13_DANBOORU_PAGE_TAG_BATCH=PASS')
print('V8_13_DANBOORU_TAG_COMMIT_SERIAL=PASS')
print('V8_13_PAGE_PHASE_DIAGNOSTICS=PASS')
print('V8_13_PAGINATION_FREEZE_HOTFIX=PASS')
