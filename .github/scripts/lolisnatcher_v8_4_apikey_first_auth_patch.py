from pathlib import Path

# v8.4 API-key-first auth was a diagnostic experiment. It is superseded by
# v8.5, which matches Danbooru's real API semantics: login + api_key together,
# verified against /profile.json before the editor treats the account as logged in.
verified_login_patch = Path(__file__).with_name('lolisnatcher_v8_5_verified_danbooru_login_patch.py')
exec(compile(verified_login_patch.read_text(encoding='utf-8'), str(verified_login_patch), 'exec'))
