from pathlib import Path

p = Path("resolver_monolithic_rc10.c")
s = p.read_text(encoding="utf-8")
original = s

# The validated RC12 invokes these three Win32 notification sounds
# only for spawn success/failure; no gameplay or UI state is changed.
assert s.count("MessageBeep(") == 3, "RC12 beep call count changed"
for token in ("MessageBeep(MB_OK);", "MessageBeep(MB_ICONHAND);"):
    assert token in s, token
s = s.replace("MessageBeep(MB_OK);", "")
s = s.replace("MessageBeep(MB_ICONHAND);", "")
assert "MessageBeep(" not in s

# Completely disable logging to disk. Keeping the interface as a no-op
# preserves every existing caller and avoids changes in spawn/UI control flow.
start = s.index("static void logf0(const char*fmt,...){")
end = s.index("static int sibling_path(", start)
log_block = s[start:end]
assert "GetTempPathW" in log_block
assert "_wfopen" in log_block
assert "AoE2DE_P3O_54800_MONOLITHIC_RC12.log" in log_block
s = (s[:start]
    + "static void logf0(const char*fmt,...){(void)fmt;}\n"
    + "static void init_log(void){g_log[0]=0;}\n\n"
    + s[end:])

assert "_wfopen" not in s
assert "GetTempPathW" not in s
assert ".log" not in s
assert "static int spawn_selected(HWND h)" in s
assert "static void load_catalog(void)" in s
assert "static LRESULT CALLBACK overlay_proc(" in s
assert "static LRESULT CALLBACK game_proc(" in s
assert s != original

p.write_text(s, encoding="utf-8")
print("RC13 SILENT delta PASS: 3 MessageBeep removed, log file I/O removed")
