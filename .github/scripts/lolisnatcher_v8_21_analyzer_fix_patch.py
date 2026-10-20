from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.21 analyzer fix {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.21 analyzer fix {label}: {p}')


booru = 'lib/src/handlers/booru_handler.dart'
replace_once(
    booru,
    """        'indexes=${indexesEnabled ? 1 : 0} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}
',
""",
    """        'indexes=${indexesEnabled ? 1 : 0} rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\\n',
""",
    'tracked-log-newline-literal',
)


database = 'lib/src/handlers/database_handler.dart'
replace_once(
    database,
    "        row == null ? false : Tools.intToBool(row['isSnatched']),\n",
    "        row == null ? false : Tools.intToBool((row['isSnatched'] as int?) ?? 0),\n",
    'tracked-snatched-int-cast',
)
replace_once(
    database,
    "        row == null ? false : Tools.intToBool(row['isFavourite']),\n",
    "        row == null ? false : Tools.intToBool((row['isFavourite'] as int?) ?? 0),\n",
    'tracked-favourite-int-cast',
)

booru_final = Path(booru).read_text(encoding='utf-8')
db_final = Path(database).read_text(encoding='utf-8')
checks = {
    'tracked log escaped newline': "rss_mb=${ProcessInfo.currentRss ~/ (1024 * 1024)}\\n'," in booru_final,
    'snatched cast': "Tools.intToBool((row['isSnatched'] as int?) ?? 0)" in db_final,
    'favourite cast': "Tools.intToBool((row['isFavourite'] as int?) ?? 0)" in db_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.21 analyzer-fix guard failed: {label}')

print('V8_21_TRACKED_LOG_LITERAL_FIX=PASS')
print('V8_21_TRACKED_SQLITE_TYPE_FIX=PASS')
print('V8_21_ANALYZER_FIX=PASS')
