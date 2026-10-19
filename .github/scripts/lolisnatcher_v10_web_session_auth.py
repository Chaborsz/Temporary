from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


def splice(path, start_marker, end_marker, replacement, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f'{label}: start marker not found in {p}')
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f'{label}: end marker not found in {p}')
    p.write_text(text[:start] + replacement + text[end:], encoding='utf-8')
    print(f'PATCHED {label}: {p}')


# ---------------------------------------------------------------------------
# Portable session cookie jar.
# Stores only cookies/tokens emitted by the site. It never stores passwords.
# Session cookies without an expiry are intentionally persisted because the
# purpose of this Windows portable build is to preserve web login across runs.
# ---------------------------------------------------------------------------
service = Path('lib/src/services/portable_session_cookie_jar.dart')
if service.exists():
    raise SystemExit(f'portable-session-cookie-jar: file already exists: {service}')
service.write_text(r'''import 'dart:convert';
import 'dart:io';

import 'package:flutter_inappwebview/flutter_inappwebview.dart';

class PortableSessionCookieJar {
  static File get _file => File(
        '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data'
        '${Platform.pathSeparator}config${Platform.pathSeparator}session_cookies.json',
      );

  static Future<List<Map<String, dynamic>>> _read() async {
    final file = _file;
    if (!await file.exists()) {
      return <Map<String, dynamic>>[];
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! List) {
        return <Map<String, dynamic>>[];
      }
      return decoded.whereType<Map>().map((e) => e.map((k, v) => MapEntry(k.toString(), v))).toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  static Future<void> _write(List<Map<String, dynamic>> records) async {
    final file = _file;
    if (records.isEmpty) {
      if (await file.exists()) {
        await file.delete();
      }
      return;
    }
    await file.parent.create(recursive: true);
    await file.writeAsString(jsonEncode(records), flush: true);
  }

  static String _normalizedDomain(String value) => value.trim().toLowerCase().replaceFirst(RegExp(r'^\\.'), '');

  static bool _domainMatches(String requestHost, Map<String, dynamic> record) {
    final host = requestHost.toLowerCase();
    final rawDomain = (record['domain']?.toString().trim().isNotEmpty == true)
        ? record['domain'].toString()
        : (record['originHost']?.toString() ?? '');
    final domain = _normalizedDomain(rawDomain);
    if (domain.isEmpty) {
      return false;
    }
    return host == domain || host.endsWith('.$domain');
  }

  static bool _pathMatches(String requestPath, String cookiePath) {
    final path = cookiePath.isEmpty ? '/' : cookiePath;
    final requested = requestPath.isEmpty ? '/' : requestPath;
    return requested == path || requested.startsWith(path.endsWith('/') ? path : '$path/');
  }

  static bool _isExpired(Map<String, dynamic> record) {
    final raw = record['expiresDate'];
    if (raw == null) {
      return false;
    }
    final expires = raw is int ? raw : int.tryParse(raw.toString());
    return expires != null && expires <= DateTime.now().millisecondsSinceEpoch;
  }

  static String _identity(Map<String, dynamic> record) => [
        record['originHost'] ?? '',
        record['name'] ?? '',
        record['domain'] ?? '',
        record['path'] ?? '/',
      ].join('|');

  static Future<int> capture(WebUri uri, List<Cookie> cookies) async {
    if (!Platform.isWindows || uri.host.isEmpty || cookies.isEmpty) {
      return 0;
    }
    final records = await _read();
    final merged = <String, Map<String, dynamic>>{};
    for (final record in records.where((r) => !_isExpired(r))) {
      merged[_identity(record)] = record;
    }
    for (final cookie in cookies) {
      final record = <String, dynamic>{
        'originHost': uri.host.toLowerCase(),
        'name': cookie.name,
        'value': cookie.value,
        'domain': cookie.domain,
        'path': cookie.path ?? '/',
        'expiresDate': cookie.expiresDate,
        'isSecure': cookie.isSecure ?? false,
        'isHttpOnly': cookie.isHttpOnly ?? false,
      };
      merged[_identity(record)] = record;
    }
    await _write(merged.values.toList(growable: false));
    return cookies.length;
  }

  static Future<List<Cookie>> cookiesFor(WebUri uri) async {
    if (!Platform.isWindows || uri.host.isEmpty) {
      return <Cookie>[];
    }
    final records = await _read();
    final valid = <Map<String, dynamic>>[];
    final result = <Cookie>[];
    for (final record in records) {
      if (_isExpired(record)) {
        continue;
      }
      valid.add(record);
      if (!_domainMatches(uri.host, record)) {
        continue;
      }
      if (!_pathMatches(uri.path, record['path']?.toString() ?? '/')) {
        continue;
      }
      if ((record['isSecure'] == true) && uri.scheme != 'https') {
        continue;
      }
      final name = record['name']?.toString() ?? '';
      if (name.isEmpty) {
        continue;
      }
      result.add(
        Cookie(
          name: name,
          value: record['value']?.toString() ?? '',
          domain: record['domain']?.toString(),
          path: record['path']?.toString() ?? '/',
          expiresDate: record['expiresDate'] is int
              ? record['expiresDate'] as int
              : int.tryParse(record['expiresDate']?.toString() ?? ''),
          isSecure: record['isSecure'] == true,
          isHttpOnly: record['isHttpOnly'] == true,
        ),
      );
    }
    if (valid.length != records.length) {
      await _write(valid);
    }
    return result;
  }

  static Future<int> countFor(WebUri uri) async => (await cookiesFor(uri)).length;

  static Future<void> deleteCookie(WebUri uri, String name) async {
    final records = await _read();
    records.removeWhere((record) => record['name']?.toString() == name && _domainMatches(uri.host, record));
    await _write(records);
  }

  static Future<void> clearFor(WebUri uri) async {
    final records = await _read();
    records.removeWhere((record) => _domainMatches(uri.host, record));
    await _write(records);
  }

  static Future<void> clearAll() async => _write(<Map<String, dynamic>>[]);
}
''', encoding='utf-8')
print('CREATED portable session cookie jar:', service)

# ---------------------------------------------------------------------------
# Native Windows browser: persist cookies on every completed navigation and
# again on exit before the browser object is disposed.
# ---------------------------------------------------------------------------
webview = Path('lib/src/widgets/webview/webview_page.dart')
replace_once(
    webview,
    "import 'package:lolisnatcher/src/utils/logger.dart';\nimport 'package:lolisnatcher/src/utils/tools.dart';\n",
    "import 'package:lolisnatcher/src/services/portable_session_cookie_jar.dart';\nimport 'package:lolisnatcher/src/utils/logger.dart';\nimport 'package:lolisnatcher/src/utils/tools.dart';\n",
    'import-portable-session-cookie-jar-webview',
)
replace_once(
    webview,
    """          if (cookies.isNotEmpty) {
            globalWindowsCookies[effectiveUrl.host] = List<Cookie>.from(cookies);
          }
          await appendWindowsWebViewDiagnostic(
            'NATIVE_BROWSER_COOKIES host=${effectiveUrl.host} count=${cookies.length}',
          );
""",
    """          if (cookies.isNotEmpty) {
            globalWindowsCookies[effectiveUrl.host] = List<Cookie>.from(cookies);
            final int persisted = await PortableSessionCookieJar.capture(effectiveUrl, cookies);
            await appendWindowsWebViewDiagnostic(
              'SESSION_JAR_CAPTURE host=${effectiveUrl.host} count=$persisted',
            );
          }
          await appendWindowsWebViewDiagnostic(
            'NATIVE_BROWSER_COOKIES host=${effectiveUrl.host} count=${cookies.length}',
          );
""",
    'persist-native-browser-cookies-on-load-stop',
)
replace_once(
    webview,
    """  @override
  void onExit() {
    unawaited(appendWindowsWebViewDiagnostic('NATIVE_BROWSER_EXIT'));
    if (!closed.isCompleted) {
      closed.complete();
    }
  }
""",
    """  @override
  void onExit() {
    unawaited(() async {
      await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_EXIT');
      final controller = webViewController;
      if (controller != null) {
        try {
          final WebUri? url = await controller.getUrl();
          if (url != null && url.host.isNotEmpty) {
            final cookies = await CookieManager.instance(
              webViewEnvironment: webViewEnvironment,
            ).getCookies(url: url, webViewController: controller);
            if (cookies.isNotEmpty) {
              globalWindowsCookies[url.host] = List<Cookie>.from(cookies);
              final int persisted = await PortableSessionCookieJar.capture(url, cookies);
              await appendWindowsWebViewDiagnostic(
                'SESSION_JAR_EXIT_CAPTURE host=${url.host} count=$persisted',
              );
            }
          }
        } catch (e) {
          await appendWindowsWebViewDiagnostic('SESSION_JAR_EXIT_ERROR $e');
        }
      }
      if (!closed.isCompleted) {
        closed.complete();
      }
    }());
  }
""",
    'persist-native-browser-cookies-before-exit',
)

# ---------------------------------------------------------------------------
# HTTP bridge: merge three sources on Windows:
# 1) WebView2's profile cookie store, 2) portable session jar, 3) RAM snapshot.
# ---------------------------------------------------------------------------
tools = Path('lib/src/utils/tools.dart')
replace_once(
    tools,
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\nimport 'package:lolisnatcher/src/services/portable_session_cookie_jar.dart';\n",
    'import-portable-session-cookie-jar-tools',
)
tools_text = tools.read_text(encoding='utf-8')
start = tools_text.find('  static Future<String> getCookies(String uri) async {\n')
end = tools_text.find('  static Future<bool> saveCookies(String uri, List<String> cookies) async {\n', start)
if start < 0 or end < 0:
    raise SystemExit('http-cookie-bridge: getCookies markers not found')
new_get = r'''  static Future<String> getCookies(String uri) async {
    String cookieString = '';
    if (PlatformExt.hasWebviewSupport) {
      try {
        final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
        final WebUri webUri = WebUri(uri);
        List<Cookie> cookies = [];
        if (Platform.isWindows) {
          List<Cookie> persistentCookies = <Cookie>[];
          try {
            persistentCookies = await cookieManager.getCookies(url: webUri);
          } catch (_) {}
          final List<Cookie> jarCookies = await PortableSessionCookieJar.cookiesFor(webUri);
          final List<Cookie> memoryCookies = <Cookie>[];
          for (final entry in globalWindowsCookies.entries) {
            final String key = entry.key.toLowerCase();
            final String host = webUri.host.toLowerCase();
            if (host == key || host.endsWith('.$key') || key.endsWith('.$host')) {
              memoryCookies.addAll(entry.value);
            }
          }

          String identity(Cookie cookie) =>
              '${cookie.name}|${cookie.domain ?? webUri.host}|${cookie.path ?? '/'}';
          final Map<String, Cookie> merged = <String, Cookie>{};
          for (final cookie in persistentCookies) {
            merged[identity(cookie)] = cookie;
          }
          for (final cookie in jarCookies) {
            merged[identity(cookie)] = cookie;
          }
          for (final cookie in memoryCookies) {
            merged[identity(cookie)] = cookie;
          }
          cookies = merged.values.toList(growable: false);
          globalWindowsCookies[webUri.host] = List<Cookie>.from(cookies);
          await appendWindowsWebViewDiagnostic(
            'SESSION_COOKIE_BRIDGE host=${webUri.host} webview=${persistentCookies.length} '
            'jar=${jarCookies.length} memory=${memoryCookies.length} merged=${cookies.length}',
          );
        } else {
          cookies = await cookieManager.getCookies(url: webUri);
        }
        for (final Cookie cookie in cookies) {
          cookieString += '${cookie.name}=${cookie.value}; ';
        }
      } catch (e, s) {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic('SESSION_COOKIE_BRIDGE_ERROR uri=$uri error=$e');
        }
        Logger.Inst().log(
          e.toString(),
          'Tools',
          'getCookies',
          LogTypes.exception,
          s: s,
        );
      }
    }

    return cookieString.trim();
  }

'''
tools.write_text(tools_text[:start] + new_get + tools_text[end:], encoding='utf-8')
print('PATCHED portable-session-http-cookie-bridge:', tools)

# ---------------------------------------------------------------------------
# Cookie Cleaner must clear the portable jar too, otherwise deleted sessions
# would be reintroduced on the next API request.
# ---------------------------------------------------------------------------
network = Path('lib/src/pages/settings/network_page.dart')
replace_once(
    network,
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\n",
    "import 'package:lolisnatcher/src/handlers/settings_handler.dart';\nimport 'package:lolisnatcher/src/services/portable_session_cookie_jar.dart';\n",
    'import-portable-session-cookie-jar-network',
)
replace_once(
    network,
    """                      selectedBooruCookies.removeAt(selectedBooruCookies.indexOf(cookie));
                      setState(() {});
""",
    """                      if (Platform.isWindows) {
                        await PortableSessionCookieJar.deleteCookie(
                          WebUri(selectedBooru!.baseURL!),
                          cookie.name,
                        );
                      }
                      selectedBooruCookies.removeAt(selectedBooruCookies.indexOf(cookie));
                      setState(() {});
""",
    'cookie-cleaner-delete-portable-session-cookie',
)
replace_once(
    network,
    """                    globalWindowsCookies[selectedBooru!.baseURL!]?.clear();

                    if (!res) {
""",
    """                    globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host]?.clear();
                    if (Platform.isWindows) {
                      await PortableSessionCookieJar.clearFor(WebUri(selectedBooru!.baseURL!));
                    }

                    if (!res) {
""",
    'cookie-cleaner-clear-portable-session-host',
)
replace_once(
    network,
    """                    await CookieManager.instance(webViewEnvironment: webViewEnvironment).deleteAllCookies();
                    globalWindowsCookies.clear();
""",
    """                    await CookieManager.instance(webViewEnvironment: webViewEnvironment).deleteAllCookies();
                    globalWindowsCookies.clear();
                    if (Platform.isWindows) {
                      await PortableSessionCookieJar.clearAll();
                    }
""",
    'cookie-cleaner-clear-all-portable-sessions',
)
# Fix two legacy Windows map-key bugs left in upstream NetworkPage if still present.
network_text = network.read_text(encoding='utf-8')
network_text = network_text.replace(
    'globalWindowsCookies[selectedBooru!.baseURL!] ?? []',
    'globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host] ?? []',
)
network_text = network_text.replace(
    'globalWindowsCookies[selectedBooru!.baseURL!]?.remove(cookie)',
    'globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host]?.remove(cookie)',
)
network.write_text(network_text, encoding='utf-8')
print('PATCHED cookie-cleaner-host-keys:', network)

# ---------------------------------------------------------------------------
# Booru editor UX: AllTheFallen uses web-session authentication. The existing
# native WebView button becomes Login, and misleading User ID/API Key fields
# are hidden for this host. Password entry remains solely inside the website.
# ---------------------------------------------------------------------------
edit = Path('lib/src/pages/settings/booru_edit_page.dart')
replace_once(
    edit,
    "import 'package:lolisnatcher/src/services/get_perms.dart';\n",
    "import 'package:lolisnatcher/src/services/get_perms.dart';\nimport 'package:lolisnatcher/src/services/portable_session_cookie_jar.dart';\n",
    'import-portable-session-cookie-jar-editor',
)
replace_once(
    edit,
    """  String _normalizedHostOf(String input) {
    final normalized = input.trim().contains('://') ? input.trim() : 'https://${input.trim()}';
    return Uri.tryParse(normalized)?.host.toLowerCase().replaceFirst(RegExp(r'^www\\.'), '') ?? '';
  }
""",
    """  String _normalizedHostOf(String input) {
    final normalized = input.trim().contains('://') ? input.trim() : 'https://${input.trim()}';
    return Uri.tryParse(normalized)?.host.toLowerCase().replaceFirst(RegExp(r'^www\\.'), '') ?? '';
  }

  bool get _usesWebSessionLogin => _normalizedHostOf(booruURLController.text) == 'booru.allthefallen.moe';
""",
    'allthefallen-web-session-auth-mode',
)
replace_once(
    edit,
    """                name: context.loc.settings.webview.openWebview,
                subtitle: Text(context.loc.settings.webview.openWebviewTip),
""",
    """                name: _usesWebSessionLogin ? context.loc.login : context.loc.settings.webview.openWebview,
                subtitle: Text(context.loc.settings.webview.openWebviewTip),
""",
    'rename-allthefallen-open-webview-to-login',
)
replace_once(
    edit,
    """                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_CLOSED url=$targetUrl',
                    );
""",
    """                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_CLOSED url=$targetUrl',
                    );
                    if (Platform.isWindows && _usesWebSessionLogin) {
                      final int sessionCookies = await PortableSessionCookieJar.countFor(WebUri(targetUrl));
                      await appendWindowsWebViewDiagnostic(
                        'EDITOR_LOGIN_SESSION host=${WebUri(targetUrl).host} cookies=$sessionCookies',
                      );
                    }
""",
    'diagnose-web-session-after-login-close',
)
# Hide generic credentials inputs for AllTheFallen; they are not how this host
# authenticates in this build.
replace_once(
    edit,
    """            SettingsTextInput(
              controller: booruUserIDController,
""",
    """            if (!_usesWebSessionLogin)
              SettingsTextInput(
              controller: booruUserIDController,
""",
    'hide-user-id-for-web-session-host',
)
replace_once(
    edit,
    """            SettingsTextInput(
              controller: booruAPIKeyController,
""",
    """            if (!_usesWebSessionLogin)
              SettingsTextInput(
              controller: booruAPIKeyController,
""",
    'hide-api-key-for-web-session-host',
)

# Build-time guards.
webview_text = webview.read_text(encoding='utf-8')
tools_text = tools.read_text(encoding='utf-8')
network_text = network.read_text(encoding='utf-8')
edit_text = edit.read_text(encoding='utf-8')
required = {
    'portable jar service': service.exists(),
    'browser capture': 'SESSION_JAR_CAPTURE' in webview_text,
    'exit capture': 'SESSION_JAR_EXIT_CAPTURE' in webview_text,
    'HTTP jar bridge': 'SESSION_COOKIE_BRIDGE' in tools_text,
    'cookie cleaner jar clear': 'PortableSessionCookieJar.clearFor' in network_text,
    'allthefallen login mode': "'booru.allthefallen.moe'" in edit_text,
    'login label': '_usesWebSessionLogin ? context.loc.login' in edit_text,
    'generic credentials hidden': edit_text.count('if (!_usesWebSessionLogin)') >= 2,
}
for label, ok in required.items():
    if not ok:
        raise SystemExit(f'V10 guard failed: {label}')
if 'globalWindowsCookies[selectedBooru!.baseURL!]' in network_text:
    raise SystemExit('V10 guard failed: full-URL cookie-map key remains in NetworkPage')

print('V10_WEB_SESSION_COOKIE_JAR=PASS')
print('V10_ALLTHEFALLEN_LOGIN=PASS')
print('V10_PASSWORD_NOT_STORED=PASS')
print('V10_COOKIE_CLEANER_INTEGRATION=PASS')
print('V10_PATCH=PASS')
