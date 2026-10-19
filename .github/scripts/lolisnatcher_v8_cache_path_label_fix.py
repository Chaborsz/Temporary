from pathlib import Path

path = Path('lib/src/pages/settings/save_cache_page.dart')
text = path.read_text(encoding='utf-8')
old = r"Cache visual comprimida: Data\cache\visual_cache.db"
new = r"Cache visual comprimida: Data\LoliSnatcher\cache\visual_cache.db"
count = text.count(old)
if count != 1:
    raise SystemExit(f'v8 cache path label: expected 1 match, found {count}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('V8_CACHE_PATH_LABEL=PASS')
