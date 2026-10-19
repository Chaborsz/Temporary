from pathlib import Path

p = Path('lib/src/pages/settings/booru_edit_page.dart')
text = p.read_text(encoding='utf-8')
anchor = "import 'package:flutter/material.dart';\n\n"
if text.count(anchor) != 1:
    raise SystemExit(f'v10-weburi-import: expected exactly one Flutter import anchor, found {text.count(anchor)}')
text = text.replace(
    anchor,
    "import 'package:flutter/material.dart';\n\nimport 'package:flutter_inappwebview/flutter_inappwebview.dart';\n\n",
    1,
)
p.write_text(text, encoding='utf-8')
if "package:flutter_inappwebview/flutter_inappwebview.dart" not in p.read_text(encoding='utf-8'):
    raise SystemExit('v10-weburi-import guard failed')
print('V10_WEBURI_IMPORT=PASS')
