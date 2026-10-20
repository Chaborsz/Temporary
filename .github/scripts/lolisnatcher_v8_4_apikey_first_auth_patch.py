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

print('V8_5_VERIFIED_LOGIN_CHAIN=PASS')
print('V8_6_ROBUST_LOGIN_VALIDATION_CHAIN=PASS')
print('V8_7_CHALLENGE_AUTH_CHAIN=PASS')
print('V8_8_IDENTITY_DIAGNOSTIC_CHAIN=PASS')
print('V8_9_GALLERY_FREEZE_HOTFIX_CHAIN=PASS')
print('V8_10_BOUNDED_VISUAL_PIPELINE_CHAIN=PASS')
print('V8_11_FREEZE_ROOTCAUSE_PATCH_CHAIN=PASS')
