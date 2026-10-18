from pathlib import Path
import textwrap

def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count} in {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED {label}: {path}")

replace_once(
    "lib/src/handlers/service_handler.dart",
    "result = Platform.environment['LOCALAPPDATA']!;",
    "result = '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data';",
    "windows-root-to-portable-data",
)

replace_once(
    "lib/src/handlers/service_handler.dart",
    '''    } else if (Platform.isWindows) {
      result = '${await getExtDir()}/LoliSnatcher/config/';
    } else if (Platform.isIOS) {''',
    '''    } else if (Platform.isWindows) {
      result = '${await getExtDir()}${Platform.pathSeparator}config${Platform.pathSeparator}';
    } else if (Platform.isIOS) {''',
    "windows-config-to-portable-data",
)

replace_once(
    "lib/src/utils/logger.dart",
    '''if (Platform.isWindows) {
      rootPath = Platform.environment['LOCALAPPDATA'];
      appDirectory = 'LoliSnatcher';
    } else if (Platform.isLinux) {''',
    '''if (Platform.isWindows) {
      rootPath = '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data';
      appDirectory = '';
    } else if (Platform.isLinux) {''',
    "windows-logs-to-portable-data",
)

replace_once(
    "lib/main.dart",
    "    webViewEnvironment = await WebViewEnvironment.create();",
    '''    final portableDataDir = Directory(
      '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data',
    );
    await portableDataDir.create(recursive: true);
    webViewEnvironment = await WebViewEnvironment.create(
      settings: WebViewEnvironmentSettings(
        userDataFolder: '${portableDataDir.path}${Platform.pathSeparator}WebView2',
      ),
    );''',
    "webview2-user-data-to-portable-data",
)

replace_once(
    "lib/src/pages/settings/language_page.dart",
    '''    /* Japanese */ AppLocale.jaJp,
    /* Turkish */ AppLocale.trTr,''',
    '''    /* Japanese */ AppLocale.jaJp,
    /* Spanish (Mexico) */ AppLocale.esMx,
    /* Turkish */ AppLocale.trTr,''',
    "enable-spanish-mexico",
)

# Replace the upstream HKCU window-state persistence with a local INI file.
win32_path = Path("windows/runner/win32_window.cpp")
win32 = win32_path.read_text(encoding="utf-8")

old_include = '#include <flutter_windows.h>\n\n#include "resource.h"'
new_include = '#include <flutter_windows.h>\n\n#include <cwchar>\n#include <iterator>\n#include <string>\n\n#include "resource.h"'
if win32.count(old_include) != 1:
    raise SystemExit("portable-window-state: include anchor changed")
win32 = win32.replace(old_include, new_include, 1)

old_helpers = r'''constexpr const wchar_t kWindowStateRegKey[] =
    L"Software\\loliSnatcher\\Window";

bool ReadRegistryDword(HKEY key, const wchar_t* name, DWORD* value) {
  DWORD size = sizeof(*value);
  DWORD type = 0;
  return RegQueryValueEx(key, name, nullptr, &type,
                         reinterpret_cast<BYTE*>(value), &size) ==
             ERROR_SUCCESS &&
         type == REG_DWORD;
}

void WriteRegistryDword(HKEY key, const wchar_t* name, LONG value) {
  const DWORD stored_value = static_cast<DWORD>(value);
  RegSetValueEx(key, name, 0, REG_DWORD,
                reinterpret_cast<const BYTE*>(&stored_value),
                sizeof(stored_value));
}
'''

new_helpers = r'''std::wstring GetPortableWindowStatePath() {
  wchar_t executable_path[MAX_PATH] = {};
  const DWORD length =
      GetModuleFileNameW(nullptr, executable_path, MAX_PATH);
  if (length == 0 || length >= MAX_PATH) {
    return L"";
  }

  std::wstring path(executable_path, length);
  const std::wstring::size_type slash = path.find_last_of(L"\\/");
  if (slash == std::wstring::npos) {
    return L"";
  }

  path.resize(slash);
  path += L"\\Data";
  if (!CreateDirectoryW(path.c_str(), nullptr) &&
      GetLastError() != ERROR_ALREADY_EXISTS) {
    return L"";
  }

  path += L"\\window-state.ini";
  return path;
}

bool ReadPortableLong(const std::wstring& path,
                      const wchar_t* name,
                      LONG* value) {
  wchar_t buffer[64] = {};
  const DWORD chars = GetPrivateProfileStringW(
      L"Window", name, nullptr, buffer,
      static_cast<DWORD>(std::size(buffer)), path.c_str());
  if (chars == 0) {
    return false;
  }

  wchar_t* end = nullptr;
  const long parsed = std::wcstol(buffer, &end, 10);
  if (end == buffer || *end != L'\0') {
    return false;
  }

  *value = static_cast<LONG>(parsed);
  return true;
}

void WritePortableLong(const std::wstring& path,
                       const wchar_t* name,
                       LONG value) {
  const std::wstring text = std::to_wstring(value);
  WritePrivateProfileStringW(L"Window", name, text.c_str(), path.c_str());
}
'''

if win32.count(old_helpers) != 1:
    raise SystemExit(
        f"portable-window-state: helper block changed (matches={win32.count(old_helpers)})"
    )
win32 = win32.replace(old_helpers, new_helpers, 1)

old_load = '''  HKEY key = nullptr;
  if (RegOpenKeyEx(HKEY_CURRENT_USER, kWindowStateRegKey, 0, KEY_READ, &key) !=
      ERROR_SUCCESS) {
    return;
  }

  DWORD left = 0;
  DWORD top = 0;
  DWORD right = 0;
  DWORD bottom = 0;
  DWORD saved_maximized = 0;
  const bool has_bounds =
      ReadRegistryDword(key, L"Left", &left) &&
      ReadRegistryDword(key, L"Top", &top) &&
      ReadRegistryDword(key, L"Right", &right) &&
      ReadRegistryDword(key, L"Bottom", &bottom);
  ReadRegistryDword(key, L"Maximized", &saved_maximized);
  RegCloseKey(key);
'''

new_load = '''  const std::wstring state_path = GetPortableWindowStatePath();
  if (state_path.empty()) {
    return;
  }

  LONG left = 0;
  LONG top = 0;
  LONG right = 0;
  LONG bottom = 0;
  LONG saved_maximized = 0;
  const bool has_bounds =
      ReadPortableLong(state_path, L"Left", &left) &&
      ReadPortableLong(state_path, L"Top", &top) &&
      ReadPortableLong(state_path, L"Right", &right) &&
      ReadPortableLong(state_path, L"Bottom", &bottom);
  ReadPortableLong(state_path, L"Maximized", &saved_maximized);
'''

if win32.count(old_load) != 1:
    raise SystemExit(
        f"portable-window-state: load block changed (matches={win32.count(old_load)})"
    )
win32 = win32.replace(old_load, new_load, 1)

old_save = '''  HKEY key = nullptr;
  if (RegCreateKeyEx(HKEY_CURRENT_USER, kWindowStateRegKey, 0, nullptr, 0,
                     KEY_WRITE, nullptr, &key, nullptr) != ERROR_SUCCESS) {
    return;
  }

  WriteRegistryDword(key, L"Left", bounds.left);
  WriteRegistryDword(key, L"Top", bounds.top);
  WriteRegistryDword(key, L"Right", bounds.right);
  WriteRegistryDword(key, L"Bottom", bounds.bottom);
  WriteRegistryDword(key, L"Maximized", maximized);
  RegCloseKey(key);
'''

new_save = '''  const std::wstring state_path = GetPortableWindowStatePath();
  if (state_path.empty()) {
    return;
  }

  WritePortableLong(state_path, L"Left", bounds.left);
  WritePortableLong(state_path, L"Top", bounds.top);
  WritePortableLong(state_path, L"Right", bounds.right);
  WritePortableLong(state_path, L"Bottom", bounds.bottom);
  WritePortableLong(state_path, L"Maximized", maximized ? 1 : 0);
'''

if win32.count(old_save) != 1:
    raise SystemExit(
        f"portable-window-state: save block changed (matches={win32.count(old_save)})"
    )
win32 = win32.replace(old_save, new_save, 1)
win32_path.write_text(win32, encoding="utf-8")
print("PATCHED windows-window-state-to-portable-ini: windows/runner/win32_window.cpp")

secure_path = Path("lib/src/handlers/secure_storage_handler.dart")
secure_old = secure_path.read_text(encoding="utf-8")
for marker in (
    "import 'package:flutter_secure_storage/flutter_secure_storage.dart';",
    "viewedUpdateChangelogForBuild,",
):
    if marker not in secure_old:
        raise SystemExit(
            f"secure-storage-portable: upstream shape changed; missing {marker!r}"
        )

secure_new = r'''import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:get_it/get_it.dart';

class SecureStorageHandler {
  static SecureStorageHandler get instance => GetIt.instance<SecureStorageHandler>();

  static SecureStorageHandler register() {
    if (!GetIt.instance.isRegistered<SecureStorageHandler>()) {
      GetIt.instance.registerSingleton(SecureStorageHandler());
    }
    return instance;
  }

  static void unregister() => GetIt.instance.unregister<SecureStorageHandler>();

  final FlutterSecureStorage storage = const FlutterSecureStorage(
    aOptions: AndroidOptions.defaultOptions,
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  File get _portableFile => File(
        '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data${Platform.pathSeparator}config${Platform.pathSeparator}portable_secure_storage.json',
      );

  Future<Map<String, String>> _readPortable() async {
    final file = _portableFile;
    if (!await file.exists()) {
      return <String, String>{};
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is Map) {
        return decoded.map((key, value) => MapEntry(key.toString(), value.toString()));
      }
    } catch (_) {
      // Treat a malformed portability state file as empty state.
    }
    return <String, String>{};
  }

  Future<void> _writePortable(Map<String, String> values) async {
    final file = _portableFile;
    await file.parent.create(recursive: true);
    await file.writeAsString(jsonEncode(values), flush: true);
  }

  Future<void> write(SecureStorageKey key, String value) async {
    if (Platform.isWindows) {
      final values = await _readPortable();
      values[key.name] = value;
      await _writePortable(values);
      return;
    }
    await storage.write(key: key.name, value: value);
  }

  Future<String?> read(SecureStorageKey key) async {
    if (Platform.isWindows) {
      return (await _readPortable())[key.name];
    }
    return storage.read(key: key.name);
  }

  Future<bool> contains(SecureStorageKey key) async {
    return await read(key) != null;
  }

  Future<void> delete(SecureStorageKey key) async {
    if (Platform.isWindows) {
      final values = await _readPortable();
      values.remove(key.name);
      if (values.isEmpty) {
        if (await _portableFile.exists()) {
          await _portableFile.delete();
        }
      } else {
        await _writePortable(values);
      }
      return;
    }
    await storage.delete(key: key.name);
  }

  Future<void> deleteAll() async {
    if (Platform.isWindows) {
      if (await _portableFile.exists()) {
        await _portableFile.delete();
      }
      return;
    }
    await storage.deleteAll();
  }
}

enum SecureStorageKey {
  viewedUpdateChangelogForBuild,
}
'''
secure_path.write_text(textwrap.dedent(secure_new), encoding="utf-8")
print(
    "PATCHED windows-secure-storage-to-portable-json: "
    "lib/src/handlers/secure_storage_handler.dart"
)

# Guards.
for p in (
    Path("lib/src/handlers/service_handler.dart"),
    Path("lib/src/utils/logger.dart"),
    Path("lib/src/handlers/secure_storage_handler.dart"),
):
    if "LOCALAPPDATA" in p.read_text(encoding="utf-8"):
        raise SystemExit(f"portable guard failed: LOCALAPPDATA remains in {p}")

if "AppLocale.esMx" not in Path(
    "lib/src/pages/settings/language_page.dart"
).read_text(encoding="utf-8"):
    raise SystemExit("locale guard failed: es-MX is not enabled")

if "userDataFolder:" not in Path("lib/main.dart").read_text(encoding="utf-8"):
    raise SystemExit("portable guard failed: WebView2 user data folder was not redirected")

win32_text = win32_path.read_text(encoding="utf-8")
if "Software\\\\loliSnatcher\\\\Window" in win32_text:
    raise SystemExit("portable guard failed: legacy window-state registry path remains")
if "window-state.ini" not in win32_text:
    raise SystemExit("portable guard failed: window-state.ini redirection missing")

print("PORTABLE_PATCH=PASS")
print("ES_MX_ENABLED=PASS")
print("WINDOW_STATE_PORTABLE=PASS")
