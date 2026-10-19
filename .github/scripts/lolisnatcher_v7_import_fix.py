from pathlib import Path

# Build trigger checkpoint: v8.8 Danbooru username/API-key diagnostics.
path = Path('lib/src/pages/settings/booru_edit_page.dart')
text = path.read_text(encoding='utf-8')

if "import 'dart:io';" not in text:
    anchor = "import 'dart:async';\n"
    if text.count(anchor) != 1:
        raise SystemExit(
            f'v7-import-fix: expected exactly one dart:async import, found {text.count(anchor)}'
        )
    text = text.replace(anchor, "import 'dart:async';\nimport 'dart:io';\n", 1)
    path.write_text(text, encoding='utf-8')
    print('PATCHED v7-booru-edit-dart-io-import')
else:
    print('v7-booru-edit-dart-io-import already present')

final = path.read_text(encoding='utf-8')
if "Platform.isWindows" not in final:
    raise SystemExit('v7-import-fix: Platform.isWindows usage missing')
if "import 'dart:io';" not in final:
    raise SystemExit('v7-import-fix: dart:io import missing')

print('V7_DART_IO_IMPORT=PASS')
