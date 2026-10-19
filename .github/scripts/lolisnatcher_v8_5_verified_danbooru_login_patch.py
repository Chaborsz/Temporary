from pathlib import Path
import subprocess

# Keep the already validated v8.5 implementation immutable and execute it from
# the commit where it was introduced. Then layer the v8.6 response-shape/login
# validation correction on top. This avoids duplicating or silently drifting
# the large v8.5 patch while preserving an auditable cumulative chain.
BUILDER_ROOT = Path(__file__).resolve().parents[2]
V8_5_CORE_COMMIT = 'aa8addb1002e4f8aa3734d2e9b4c567ef9d07efd'
V8_5_CORE_PATH = '.github/scripts/lolisnatcher_v8_5_verified_danbooru_login_patch.py'

core = subprocess.check_output(
    [
        'git',
        '-C',
        str(BUILDER_ROOT),
        'show',
        f'{V8_5_CORE_COMMIT}:{V8_5_CORE_PATH}',
    ],
    text=True,
)
exec(compile(core, f'{V8_5_CORE_PATH}@{V8_5_CORE_COMMIT}', 'exec'))

v8_6 = Path(__file__).with_name('lolisnatcher_v8_6_danbooru_login_validation_patch.py')
exec(compile(v8_6.read_text(encoding='utf-8'), str(v8_6), 'exec'))

print('V8_5_CORE_PINNED=PASS')
print('V8_6_CHAINED=PASS')
