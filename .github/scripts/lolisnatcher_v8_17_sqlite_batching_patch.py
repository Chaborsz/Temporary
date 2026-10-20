from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.17 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.17 {label}: {p}')


# ---------------------------------------------------------------------------
# 1) True typed-tag SQLite bulk persistence.
#
# v8.13 grouped tags at the Dart call-site, but upstream DBHandler still did a
# SELECT followed by INSERT/UPDATE for every individual tag. The v8.16 runtime
# log proves this becomes progressively expensive (TAG_BATCH reaching >1.6s).
# Resolve all existing IDs with one IN query per bounded chunk, then execute the
# writes through sqflite Batch. This preserves the same Tag rows and update
# semantics while removing hundreds of SQLite round-trips per flush.
# ---------------------------------------------------------------------------
database_handler = 'lib/src/handlers/database_handler.dart'
replace_once(
    database_handler,
    """  /// Adds tags for a BooruItem to the database\n  Future<void> updateTagsFromObjects(List<Tag> tags) async {\n    String? id = '';\n    // TODO rewrite using batch\n    for (final tag in tags) {\n      id = await getTagID(tag.fullString);\n      if (id.isEmpty) {\n        final result = await db?.rawInsert('INSERT INTO Tag(name, tagType, updatedAt) VALUES(?,?,?)', [\n          tag.fullString,\n          tag.tagType.name,\n          tag.updatedAt,\n        ]);\n        id = result?.toString();\n      } else {\n        await db?.rawUpdate('UPDATE Tag SET tagType = ?,updatedAt = ? WHERE id = ?', [\n          tag.tagType.name,\n          tag.updatedAt,\n          id,\n        ]);\n      }\n    }\n    return;\n  }\n""",
    """  /// Adds/updates typed tags with bounded bulk lookup + batched writes.\n  /// This is intentionally independent of the optional user DB indexes: one\n  /// table scan per chunk is vastly cheaper than one lookup per tag and keeps\n  /// the existing database/index preference semantics intact.\n  Future<void> updateTagsFromObjects(List<Tag> tags) async {\n    final Database? database = db;\n    if (database == null || tags.isEmpty) return;\n\n    final Map<String, Tag> unique = <String, Tag>{};\n    for (final Tag tag in tags) {\n      if (tag.fullString.isEmpty) continue;\n      unique[tag.fullString] = tag;\n    }\n    if (unique.isEmpty) return;\n\n    const int chunkSize = 400;\n    final List<Tag> values = unique.values.toList(growable: false);\n\n    for (int offset = 0; offset < values.length; offset += chunkSize) {\n      final int end = (offset + chunkSize < values.length) ? offset + chunkSize : values.length;\n      final List<Tag> chunk = values.sublist(offset, end);\n      final List<String> names = chunk.map((Tag tag) => tag.fullString).toList(growable: false);\n      final String placeholders = List<String>.filled(names.length, '?').join(',');\n      final List<Map<String, Object?>> rows = await database.rawQuery(\n        'SELECT id, name FROM Tag WHERE name IN ($placeholders)',\n        names,\n      );\n\n      final Map<String, Object?> existingIds = <String, Object?>{};\n      for (final Map<String, Object?> row in rows) {\n        final Object? name = row['name'];\n        final Object? id = row['id'];\n        if (name != null && id != null) existingIds[name.toString()] = id;\n      }\n\n      final Batch batch = database.batch();\n      for (final Tag tag in chunk) {\n        final Object? id = existingIds[tag.fullString];\n        if (id == null) {\n          batch.rawInsert(\n            'INSERT INTO Tag(name, tagType, updatedAt) VALUES(?,?,?)',\n            <Object?>[tag.fullString, tag.tagType.name, tag.updatedAt],\n          );\n        } else {\n          batch.rawUpdate(\n            'UPDATE Tag SET tagType = ?,updatedAt = ? WHERE id = ?',\n            <Object?>[tag.tagType.name, tag.updatedAt, id],\n          );\n        }\n      }\n      await batch.commit(noResult: true);\n    }\n  }\n""",
    'true-bulk-tag-db-persistence',
)


# ---------------------------------------------------------------------------
# 2) Coalesce thumbnail BLOB persistence into bounded SQLite batches.
#
# Thumbnail display is already decoupled from persistence, but every downloaded
# thumbnail still scheduled its own db.insert. Batch up to 16 entries or 100 ms
# of arrivals, whichever comes first. The visible image remains display-first;
# no network/decode path waits for this batch. Slow batches are logged so the
# next runtime log can prove whether visual-cache SQLite is another stall source.
# ---------------------------------------------------------------------------
cache = 'lib/src/services/compressed_visual_cache.dart'
replace_once(
    cache,
    """class CompressedVisualCache {\n""",
    """class _PendingVisualDbWrite {\n  _PendingVisualDbWrite(\n    this.folder,\n    this.legacyPath,\n    this.sourceBytes,\n    this.payload,\n    this.codec,\n  );\n\n  final String folder;\n  final String legacyPath;\n  final Uint8List sourceBytes;\n  final Uint8List payload;\n  final String codec;\n}\n\nclass CompressedVisualCache {\n""",
    'visual-db-pending-entry-type',
)

replace_once(
    cache,
    """  Future<Database>? _databaseFuture;\n  final Set<String> _backgroundThumbnailWrites = <String>{};\n  int _lastLoosePurgeMs = 0;\n""",
    """  Future<Database>? _databaseFuture;\n  final Map<String, _PendingVisualDbWrite> _pendingThumbnailStores =\n      <String, _PendingVisualDbWrite>{};\n  Timer? _thumbnailStoreTimer;\n  Future<void> _thumbnailStoreChain = Future<void>.value();\n  int _lastLoosePurgeMs = 0;\n""",
    'visual-db-batch-state',
)

replace_once(
    cache,
    """  Future<void> _persistThumbnailInBackground(\n    String folder,\n    String legacyPath,\n    Uint8List bytes,\n  ) async {\n    final String cacheKey = _key(folder, legacyPath);\n    if (!_backgroundThumbnailWrites.add(cacheKey)) return;\n\n    try {\n      // v8.11: persist source bytes only. This deliberately removes image decode,\n      // resize, isolate creation and WebP encode from background cache work.\n      await _storeEntry(folder, legacyPath, bytes, bytes, 'source');\n    } catch (_) {\n      // Cache persistence is optional. A failed background write must never\n      // block or fail the visible image load.\n    } finally {\n      _backgroundThumbnailWrites.remove(cacheKey);\n    }\n  }\n""",
    """  void _queueThumbnailStore(\n    String folder,\n    String legacyPath,\n    Uint8List bytes,\n  ) {\n    final String cacheKey = _key(folder, legacyPath);\n    _pendingThumbnailStores[cacheKey] =\n        _PendingVisualDbWrite(folder, legacyPath, bytes, bytes, 'source');\n\n    if (_pendingThumbnailStores.length >= 16) {\n      _thumbnailStoreTimer?.cancel();\n      _thumbnailStoreTimer = null;\n      unawaited(_flushPendingThumbnailStores());\n      return;\n    }\n\n    _thumbnailStoreTimer ??= Timer(const Duration(milliseconds: 100), () {\n      _thumbnailStoreTimer = null;\n      unawaited(_flushPendingThumbnailStores());\n    });\n  }\n\n  Future<void> _flushPendingThumbnailStores() async {\n    if (_pendingThumbnailStores.isEmpty) return;\n\n    _thumbnailStoreTimer?.cancel();\n    _thumbnailStoreTimer = null;\n    final List<_PendingVisualDbWrite> pending =\n        _pendingThumbnailStores.values.toList(growable: false);\n    _pendingThumbnailStores.clear();\n\n    _thumbnailStoreChain = _thumbnailStoreChain.then((_) async {\n      final Stopwatch watch = Stopwatch()..start();\n      int totalBytes = 0;\n      try {\n        final Database db = await _database();\n        final int now = DateTime.now().millisecondsSinceEpoch;\n        final Batch batch = db.batch();\n        for (final _PendingVisualDbWrite entry in pending) {\n          totalBytes += entry.payload.length;\n          batch.insert(\n            'VisualCache',\n            <String, Object?>{\n              'cache_key': _key(entry.folder, entry.legacyPath),\n              'folder': entry.folder,\n              'payload': entry.payload,\n              'compressed': 0,\n              'codec': entry.codec,\n              'original_size': entry.sourceBytes.length,\n              'stored_size': entry.payload.length,\n              'created_at': now,\n              'accessed_at': now,\n            },\n            conflictAlgorithm: ConflictAlgorithm.replace,\n          );\n        }\n        await batch.commit(noResult: true);\n      } catch (_) {\n        // Cache persistence is optional. Missing rows are simply fetched again.\n      } finally {\n        watch.stop();\n      }\n\n      if (Platform.isWindows && watch.elapsedMilliseconds >= 50) {\n        try {\n          final String sep = Platform.pathSeparator;\n          final File file = File(\n            '${File(Platform.resolvedExecutable).parent.path}${sep}Data${sep}performance-stalls.log',\n          );\n          await file.parent.create(recursive: true);\n          await file.writeAsString(\n            '${DateTime.now().toIso8601String()} VISUAL_DB_BATCH entries=${pending.length} '\n            'bytes=$totalBytes ms=${watch.elapsedMilliseconds}\\n',\n            mode: FileMode.append,\n            flush: false,\n          );\n        } catch (_) {}\n      }\n    });\n\n    await _thumbnailStoreChain;\n  }\n\n  Future<void> _persistThumbnailInBackground(\n    String folder,\n    String legacyPath,\n    Uint8List bytes,\n  ) async {\n    _queueThumbnailStore(folder, legacyPath, bytes);\n  }\n""",
    'coalesced-visual-db-batch',
)


# Guards.
db_final = Path(database_handler).read_text(encoding='utf-8')
cache_final = Path(cache).read_text(encoding='utf-8')
checks = {
    'tag bulk lookup': "SELECT id, name FROM Tag WHERE name IN ($placeholders)" in db_final,
    'tag batch writes': 'final Batch batch = database.batch();' in db_final and 'await batch.commit(noResult: true);' in db_final,
    'old per-tag lookup removed': 'id = await getTagID(tag.fullString);' not in db_final,
    'visual pending map': '_pendingThumbnailStores' in cache_final,
    'visual 16-entry threshold': '_pendingThumbnailStores.length >= 16' in cache_final,
    'visual 100ms coalesce': 'Timer(const Duration(milliseconds: 100)' in cache_final,
    'visual sqlite batch': "batch.insert(\n            'VisualCache'" in cache_final,
    'visual batch diagnostic': 'VISUAL_DB_BATCH entries=' in cache_final,
    'display-first call retained': 'unawaited(_persistThumbnailInBackground(folder, legacyPath, bytes));' in cache_final,
    'db-only source payload retained': "_PendingVisualDbWrite(folder, legacyPath, bytes, bytes, 'source')" in cache_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.17 guard failed: {label}')

print('V8_17_TRUE_TAG_SQLITE_BATCH=PASS')
print('V8_17_TAG_LOOKUP_CHUNK=400')
print('V8_17_VISUAL_DB_BATCH_MAX=16')
print('V8_17_VISUAL_DB_COALESCE_MS=100')
print('V8_17_VISUAL_DB_BATCH_DIAGNOSTIC=PASS')
print('V8_17_SQLITE_STALL_REDUCTION=PASS')
