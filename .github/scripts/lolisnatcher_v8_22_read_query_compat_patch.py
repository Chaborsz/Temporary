from pathlib import Path

path = Path('lib/src/services/compressed_visual_cache.dart')
text = path.read_text(encoding='utf-8')
old = "      columns: <String>['payload', 'accessed_at'],\n"
new = "      columns: <String>['payload', 'compressed', 'accessed_at'],\n"
count = text.count(old)
if count != 1:
    raise SystemExit(f'v8.22 read-query compat: expected 1 match, found {count}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('V8_22_READ_QUERY_COMPAT=PASS')
