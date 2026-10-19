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

print('V8_5_VERIFIED_LOGIN_CHAIN=PASS')
print('V8_6_ROBUST_LOGIN_VALIDATION_CHAIN=PASS')
