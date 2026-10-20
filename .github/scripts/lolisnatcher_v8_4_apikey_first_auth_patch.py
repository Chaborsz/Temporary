from pathlib import Path

# v8.4 API-key-first auth was a diagnostic experiment. It is superseded by
# v8.5, which matches Danbooru's real API semantics: login + api_key together.
verified_login_patch = Path(__file__).with_name('lolisnatcher_v8_5_verified_danbooru_login_patch.py')
exec(compile(verified_login_patch.read_text(encoding='utf-8'), str(verified_login_patch), 'exec'))

# v8.6 keeps the v8.5 auth semantics but makes identity validation tolerant of
# real-world response shapes: users.json first, profile.json compatibility
# fallback, and manual JSON decoding when a server returns JSON as text.
robust_validation_patch = Path(__file__).with_name('lolisnatcher_v8_6_danbooru_login_validation_patch.py')
exec(compile(robust_validation_patch.read_text(encoding='utf-8'), str(robust_validation_patch), 'exec'))

# v8.7 fixes validation requests that end on HTML instead of the JSON API by
# normalizing the API root, using Basic Auth with query fallback, and applying
# the same captcha/anti-bot interceptor used by normal searches.
challenge_auth_patch = Path(__file__).with_name('lolisnatcher_v8_7_danbooru_challenge_auth_patch.py')
exec(compile(challenge_auth_patch.read_text(encoding='utf-8'), str(challenge_auth_patch), 'exec'))

# v8.8 separates username validity from API-key validity: resolve the public
# canonical Danbooru username/ID first, then authenticate that exact account.
identity_diagnostic_patch = Path(__file__).with_name('lolisnatcher_v8_8_danbooru_identity_diagnostic_patch.py')
exec(compile(identity_diagnostic_patch.read_text(encoding='utf-8'), str(identity_diagnostic_patch), 'exec'))

# v8.9 removes WebP encode/SQLite persistence from the visible thumbnail load
# path, serializes conversion to one worker, deduplicates background writes and
# makes LRU timestamp maintenance non-blocking.
gallery_freeze_hotfix = Path(__file__).with_name('lolisnatcher_v8_9_gallery_freeze_hotfix.py')
exec(compile(gallery_freeze_hotfix.read_text(encoding='utf-8'), str(gallery_freeze_hotfix), 'exec'))

# v8.10 bounds the complete Windows thumbnail/sample load+decode pipeline and
# increases list/grid debounce so fast scrolling discards more obsolete work.
bounded_visual_pipeline = Path(__file__).with_name('lolisnatcher_v8_10_bounded_visual_pipeline.py')
exec(compile(bounded_visual_pipeline.read_text(encoding='utf-8'), str(bounded_visual_pipeline), 'exec'))

# v8.11 makes that gate cancellation-aware, stops forced ImageCache eviction,
# disables WebP background conversion entirely, migrates old WebP thumbnail rows
# out of the packed cache, and records low-overhead frame/event-loop stalls.
freeze_rootcause_patch = Path(__file__).with_name('lolisnatcher_v8_11_freeze_rootcause_patch.py')
exec(compile(freeze_rootcause_patch.read_text(encoding='utf-8'), str(freeze_rootcause_patch), 'exec'))

# v8.12 enforces the intended Windows cache invariant: grid uses thumbnailURL
# only, samples are viewer-only and memory-only, and thumbnails/samples can no
# longer be written/read as loose legacy files beside visual_cache.db.
visual_cache_integrity_patch = Path(__file__).with_name('lolisnatcher_v8_12_visual_cache_integrity_patch.py')
exec(compile(visual_cache_integrity_patch.read_text(encoding='utf-8'), str(visual_cache_integrity_patch), 'exec'))

# v8.13 removes Danbooru's per-post/per-tag SQLite write storm by collecting
# typed tags per page, bulk-writing each category and serializing page commits.
# It also records page parse/merge timings in performance-stalls.log.
pagination_freeze_patch = Path(__file__).with_name('lolisnatcher_v8_13_danbooru_page_batch_patch.py')
exec(compile(pagination_freeze_patch.read_text(encoding='utf-8'), str(pagination_freeze_patch), 'exec'))

# v8.14 uses an append-only filter path for Danbooru pages, removes the
# redundant second tag scan/type queue, defers tracked-value lookup and moves
# typed-tag persistence away from the immediate page boundary.
incremental_catalog_merge_patch = Path(__file__).with_name('lolisnatcher_v8_14_incremental_catalog_merge_patch.py')
exec(compile(incremental_catalog_merge_patch.read_text(encoding='utf-8'), str(incremental_catalog_merge_patch), 'exec'))

# v8.15 makes the visual-cache invariant structural: packed Windows thumbnails
# use logical SQLite keys without ever constructing loose samples/thumbnails
# paths, ImageWriter forbids physical visual-cache paths, and all Thumbnail
# widgets on Windows are thumbnailURL-only.
strict_db_only_visual_cache_patch = Path(__file__).with_name('lolisnatcher_v8_15_strict_db_only_visual_cache_patch.py')
exec(compile(strict_db_only_visual_cache_patch.read_text(encoding='utf-8'), str(strict_db_only_visual_cache_patch), 'exec'))

# v8.16 serializes the complete Windows thumbnail load/decode pipeline and
# moves typed Danbooru tag persistence into a 2.5s idle/coalescing window so
# SQLite work does not compete with the thumbnail burst at page boundaries.
visual_decode_and_tag_idle_patch = Path(__file__).with_name('lolisnatcher_v8_16_visual_decode_and_tag_idle_patch.py')
exec(compile(visual_decode_and_tag_idle_patch.read_text(encoding='utf-8'), str(visual_decode_and_tag_idle_patch), 'exec'))

print('V8_5_VERIFIED_LOGIN_CHAIN=PASS')
print('V8_6_ROBUST_LOGIN_VALIDATION_CHAIN=PASS')
print('V8_7_CHALLENGE_AUTH_CHAIN=PASS')
print('V8_8_IDENTITY_DIAGNOSTIC_CHAIN=PASS')
print('V8_9_GALLERY_FREEZE_HOTFIX_CHAIN=PASS')
print('V8_10_BOUNDED_VISUAL_PIPELINE_CHAIN=PASS')
print('V8_11_FREEZE_ROOTCAUSE_PATCH_CHAIN=PASS')
print('V8_12_VISUAL_CACHE_INTEGRITY_CHAIN=PASS')
print('V8_13_PAGINATION_FREEZE_HOTFIX_CHAIN=PASS')
print('V8_14_CATALOG_MERGE_HOTFIX_CHAIN=PASS')
print('V8_15_STRICT_DB_ONLY_VISUAL_CACHE_CHAIN=PASS')
print('V8_16_FRAME_STALL_REDUCTION_CHAIN=PASS')
