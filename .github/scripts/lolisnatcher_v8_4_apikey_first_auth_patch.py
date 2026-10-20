from pathlib import Path

# Canonical cumulative patch chain after the superseded v8.4 auth experiment.
# Each script is executed in order against the same patched source tree.
_chain = [
    ('lolisnatcher_v8_5_verified_danbooru_login_patch.py', 'V8_5_VERIFIED_LOGIN_CHAIN=PASS'),
    ('lolisnatcher_v8_6_danbooru_login_validation_patch.py', 'V8_6_ROBUST_LOGIN_VALIDATION_CHAIN=PASS'),
    ('lolisnatcher_v8_7_danbooru_challenge_auth_patch.py', 'V8_7_CHALLENGE_AUTH_CHAIN=PASS'),
    ('lolisnatcher_v8_8_danbooru_identity_diagnostic_patch.py', 'V8_8_IDENTITY_DIAGNOSTIC_CHAIN=PASS'),
    ('lolisnatcher_v8_9_gallery_freeze_hotfix.py', 'V8_9_GALLERY_FREEZE_HOTFIX_CHAIN=PASS'),
    ('lolisnatcher_v8_10_bounded_visual_pipeline.py', 'V8_10_BOUNDED_VISUAL_PIPELINE_CHAIN=PASS'),
    ('lolisnatcher_v8_11_freeze_rootcause_patch.py', 'V8_11_FREEZE_ROOTCAUSE_PATCH_CHAIN=PASS'),
    ('lolisnatcher_v8_12_visual_cache_integrity_patch.py', 'V8_12_VISUAL_CACHE_INTEGRITY_CHAIN=PASS'),
    ('lolisnatcher_v8_13_danbooru_page_batch_patch.py', 'V8_13_PAGINATION_FREEZE_HOTFIX_CHAIN=PASS'),
    ('lolisnatcher_v8_14_incremental_catalog_merge_patch.py', 'V8_14_CATALOG_MERGE_HOTFIX_CHAIN=PASS'),
    ('lolisnatcher_v8_15_strict_db_only_visual_cache_patch.py', 'V8_15_STRICT_DB_ONLY_VISUAL_CACHE_CHAIN=PASS'),
    ('lolisnatcher_v8_16_visual_decode_and_tag_idle_patch.py', 'V8_16_FRAME_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_17_sqlite_batching_patch.py', 'V8_17_SQLITE_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_18_http_codec_stall_patch.py', 'V8_18_HTTP_CODEC_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_19_tag_idle_batch_patch.py', 'V8_19_TAG_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_20_cooperative_tag_map_patch.py', 'V8_20_EVENT_LOOP_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_21_tracked_lookup_watchdog_patch.py', 'V8_21_POST_PAGE_STALL_REDUCTION_CHAIN=PASS'),
    ('lolisnatcher_v8_21_analyzer_fix_patch.py', 'V8_21_ANALYZER_FIX_CHAIN=PASS'),
    ('lolisnatcher_v8_22_visual_db_memory_stall_patch.py', 'V8_22_VISUAL_MEMORY_STALL_REDUCTION_CHAIN=PASS'),
]

for filename, marker in _chain:
    patch = Path(__file__).with_name(filename)
    exec(compile(patch.read_text(encoding='utf-8'), str(patch), 'exec'))
    print(marker)
