from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.14 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.14 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) Generic filter fast path for appended pages.
#
# Full filterFetched() is still retained for settings/state changes, but normal
# pagination should not rescan/recompare every previously fetched item. Filter
# only the new page against the already-visible dedupe keys and append once.
# ---------------------------------------------------------------------------
booru_handler = 'lib/src/handlers/booru_handler.dart'
replace_once(
    booru_handler,
    """    if (!listEquals(itemsBeforeFilter, filteredItems)) {
      filteredFetched.value = filteredItems;
    }
  }

  String get className => runtimeType.toString();
""",
    """    if (!listEquals(itemsBeforeFilter, filteredItems)) {
      filteredFetched.value = filteredItems;
    }
  }

  /// Fast path for ordinary pagination. Existing items have already passed the
  /// current filters, so only evaluate the newly fetched page and preserve the
  /// same URL/server-id duplicate rules. Full filterFetched() remains the source
  /// of truth when filters or item state are explicitly refreshed.
  void appendFilteredFetchedPage(List<BooruItem> newItems) {
    if (newItems.isEmpty) return;

    final SettingsHandler settingsHandler = SettingsHandler.instance;
    final bool filterFavourites = settingsHandler.filterFavourites && booru.type?.isFavourites != true;
    final bool filterSnatched = settingsHandler.filterSnatched && booru.type?.isDownloads != true;
    final Set<String> seenFileUrls = <String>{
      for (final BooruItem item in filteredFetched)
        if (item.fileURL.isNotEmpty) item.fileURL,
    };
    final Set<String> seenServerIds = <String>{
      for (final BooruItem item in filteredFetched)
        if (item.serverId != null) item.serverId!,
    };
    final List<BooruItem> filteredItems = <BooruItem>[];

    for (final BooruItem item in newItems) {
      if (!ContentPolicy.isItemAllowed(booru, item)) continue;
      if (settingsHandler.filterHated && item.isHidden) continue;
      if (settingsHandler.filterMarked && item.isMarked) continue;
      if (settingsHandler.filterAi && item.isAI) continue;
      if (filterFavourites && item.isFavourite.value == true) continue;
      if (filterSnatched && item.isSnatched.value == true) continue;

      final String? serverId = item.serverId;
      final bool duplicateFileUrl = item.fileURL.isNotEmpty && seenFileUrls.contains(item.fileURL);
      final bool duplicateServerId = serverId != null && seenServerIds.contains(serverId);
      if (duplicateFileUrl || duplicateServerId) continue;

      if (item.fileURL.isNotEmpty) seenFileUrls.add(item.fileURL);
      if (serverId != null) seenServerIds.add(serverId);
      filteredItems.add(item);
    }

    if (filteredItems.isNotEmpty) {
      filteredFetched.addAll(filteredItems);
    }
  }

  String get className => runtimeType.toString();
""",
    'incremental-filter-fast-path',
)


# ---------------------------------------------------------------------------
# 2) Generic tag population dedupe was O(n^2) because List.contains() ran for
# every tag in every item. Keep behavior identical but dedupe with a Set.
# Danbooru v8.14 will no longer need this second pass at all because its API
# already provides every tag category explicitly.
# ---------------------------------------------------------------------------
replace_once(
    booru_handler,
    """  Future<void> populateTagHandler(List<BooruItem> items) async {
    final List<String> unTyped = [];
    for (int x = 0; x < items.length; x++) {
      for (int i = 0; i < items[x].tagsList.length; i++) {
        final Tag tag = items[x].tagsList[i];

        final bool alreadyStoredAndNotStale = TagHandler.instance.hasTagAndNotStale(
          tag.fullString,
        ); //TagHandler.instance.hasTag(tag);
        if (!alreadyStoredAndNotStale) {
          final bool isPresent = unTyped.contains(tag.fullString);
          if (!isPresent) {
            unTyped.add(tag.fullString);
          }
        }
      }
    }

    if (unTyped.isNotEmpty) {
      TagHandler.instance.queue(unTyped, booru, 200);
    }
  }
""",
    """  Future<void> populateTagHandler(List<BooruItem> items) async {
    final Set<String> unTyped = <String>{};
    for (final BooruItem item in items) {
      for (final Tag tag in item.tagsList) {
        if (!TagHandler.instance.hasTagAndNotStale(tag.fullString)) {
          unTyped.add(tag.fullString);
        }
      }
    }

    if (unTyped.isNotEmpty) {
      TagHandler.instance.queue(unTyped.toList(growable: false), booru, 200);
    }
  }
""",
    'linear-tag-population-dedupe',
)


# ---------------------------------------------------------------------------
# 3) Danbooru-specific merge.
#
# v8.13 still called super.afterParseResponse(), which performed a full-history
# filter plus populateTagHandler(). The latter was redundant for Danbooru and
# mostly synchronous despite unawaited(). Replace it with an append-only merge,
# defer tracked-value DB lookup to the next event turn, and schedule typed-tag
# persistence after the page has had time to render.
# ---------------------------------------------------------------------------
danbooru = 'lib/src/boorus/danbooru_handler.dart'
replace_once(
    danbooru,
    """  @override
  Future<void> afterParseResponse(List<BooruItem> newItems) async {
    final Map<TagType, List<String>> batches = <TagType, List<String>>{
      for (final MapEntry<TagType, Set<String>> entry in _pageTypedTags.entries)
        entry.key: entry.value.toList(growable: false),
    };
    for (final Set<String> tags in _pageTypedTags.values) {
      tags.clear();
    }

    await super.afterParseResponse(newItems);

    if (batches.values.any((List<String> tags) => tags.isNotEmpty)) {
      _tagCommitChain = _tagCommitChain.then((_) => _commitPageTags(batches));
      unawaited(_tagCommitChain);
    }
  }
""",
    """  @override
  Future<void> afterParseResponse(List<BooruItem> newItems) async {
    final Map<TagType, List<String>> batches = <TagType, List<String>>{
      for (final MapEntry<TagType, Set<String>> entry in _pageTypedTags.entries)
        entry.key: entry.value.toList(growable: false),
    };
    for (final Set<String> tags in _pageTypedTags.values) {
      tags.clear();
    }

    final int lengthBefore = fetched.length;
    if (lengthBefore == 0 && filteredFetched.isNotEmpty) {
      // A new search resets fetched before parsing its first page. Match the
      // old full-filter behavior by dropping the previous visible result set.
      filteredFetched.clear();
    }

    fetched.addAll(newItems);
    appendFilteredFetchedPage(newItems);

    // Do not run even the small tracked-value DB setup on the page-merge stack.
    // Yield one event turn so Flutter can present the newly appended cards first.
    unawaited(
      Future<void>.delayed(
        Duration.zero,
        () => setMultipleTrackedValues(lengthBefore, fetched.length),
      ),
    );

    // Danbooru already supplied general/character/copyright/artist/meta tags in
    // this response, so populateTagHandler(newItems) would only rescan the same
    // tags and enqueue redundant type lookups. The five typed batches above are
    // complete for this provider.
    if (batches.values.any((List<String> tags) => tags.isNotEmpty)) {
      _tagCommitChain = _tagCommitChain.then((_) async {
        // Keep SQLite/tag-map maintenance away from the immediate page boundary.
        await Future<void>.delayed(const Duration(milliseconds: 250));
        await _commitPageTags(batches);
      });
      unawaited(_tagCommitChain);
    }
  }
""",
    'danbooru-incremental-merge',
)


# Guards.
booru_final = Path(booru_handler).read_text(encoding='utf-8')
dan_final = Path(danbooru).read_text(encoding='utf-8')
checks = {
    'incremental filter exists': 'void appendFilteredFetchedPage(List<BooruItem> newItems)' in booru_final,
    'incremental filter appends once': 'filteredFetched.addAll(filteredItems);' in booru_final,
    'generic tag dedupe is set': 'final Set<String> unTyped = <String>{};' in booru_final,
    'generic tag O(n2) contains removed': 'unTyped.contains(tag.fullString)' not in booru_final,
    'Danbooru no super merge': 'await super.afterParseResponse(newItems);' not in dan_final,
    'Danbooru incremental merge': 'appendFilteredFetchedPage(newItems);' in dan_final,
    'tracked values deferred': 'Future<void>.delayed(\n        Duration.zero' in dan_final,
    'redundant Danbooru population skipped': 'populateTagHandler(newItems)' not in dan_final,
    'tag persistence deferred': 'Duration(milliseconds: 250)' in dan_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.14 guard failed: {label}')

print('V8_14_INCREMENTAL_FILTER_APPEND=PASS')
print('V8_14_LINEAR_TAG_DEDUPE=PASS')
print('V8_14_DANBOORU_REDUNDANT_TAG_PASS_REMOVED=PASS')
print('V8_14_TRACKED_VALUES_DEFERRED=PASS')
print('V8_14_TAG_PERSISTENCE_DEFERRED=PASS')
print('V8_14_CATALOG_MERGE_HOTFIX=PASS')
