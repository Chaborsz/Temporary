from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


tools = Path('lib/src/utils/tools.dart')
old_get = r'''  static Future<String> getCookies(String uri) async {
    String cookieString = '';
    if (PlatformExt.hasWebviewSupport) {
      try {
        final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
        List<Cookie> cookies = [];
        if (Platform.isWindows) {
          cookies.addAll(globalWindowsCookies[WebUri(uri).host] ?? []);
        } else {
          cookies = await cookieManager.getCookies(url: WebUri(uri));
        }
        for (final Cookie cookie in cookies) {
          cookieString += '${cookie.name}=${cookie.value}; ';
        }
      } catch (e, s) {
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
new_get = r'''  static Future<String> getCookies(String uri) async {
    String cookieString = '';
    if (PlatformExt.hasWebviewSupport) {
      try {
        final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
        final WebUri webUri = WebUri(uri);
        List<Cookie> cookies = [];
        if (Platform.isWindows) {
          // Windows WebView2 keeps its cookie store in the persistent portable
          // Data\\WebView2 profile.  The upstream implementation only reads
          // globalWindowsCookies, which is process-local RAM and therefore
          // loses authentication after app restart.  Read the actual WebView2
          // cookie store first and merge any fresher in-memory cookies on top.
          final List<Cookie> persistentCookies = await cookieManager.getCookies(url: webUri);
          final List<Cookie> memoryCookies = globalWindowsCookies[webUri.host] ?? const <Cookie>[];
          final Map<String, Cookie> merged = <String, Cookie>{};

          String cookieIdentity(Cookie cookie) =>
              '${cookie.name}|${cookie.domain ?? ''}|${cookie.path ?? '/'}';

          for (final Cookie cookie in persistentCookies) {
            merged[cookieIdentity(cookie)] = cookie;
          }
          for (final Cookie cookie in memoryCookies) {
            merged[cookieIdentity(cookie)] = cookie;
          }

          cookies = merged.values.toList(growable: false);
          globalWindowsCookies[webUri.host] = List<Cookie>.from(cookies);
          await appendWindowsWebViewDiagnostic(
            'COOKIE_BRIDGE_READ host=${webUri.host} persistent=${persistentCookies.length} '
            'memory=${memoryCookies.length} merged=${cookies.length}',
          );
        } else {
          cookies = await cookieManager.getCookies(url: webUri);
        }
        for (final Cookie cookie in cookies) {
          cookieString += '${cookie.name}=${cookie.value}; ';
        }
      } catch (e, s) {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic('COOKIE_BRIDGE_READ_ERROR uri=$uri error=$e');
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
replace_once(tools, old_get, new_get, 'persistent-webview2-cookie-read')

old_save = r'''          if (Platform.isWindows) {
            globalWindowsCookies[WebUri(uri).host]?.add(cookie);
          }
'''
new_save = r'''          if (Platform.isWindows) {
            final String host = WebUri(uri).host;
            final List<Cookie> hostCookies = globalWindowsCookies.putIfAbsent(host, () => <Cookie>[]);
            hostCookies.removeWhere(
              (existing) =>
                  existing.name == cookie.name &&
                  (existing.domain ?? '') == (cookie.domain ?? '') &&
                  (existing.path ?? '/') == (cookie.path ?? '/'),
            );
            hostCookies.add(cookie);
          }
'''
replace_once(tools, old_save, new_save, 'windows-cookie-memory-upsert')

network = Path('lib/src/pages/settings/network_page.dart')
replace_once(
    network,
    "selectedBooruCookies.addAll(globalWindowsCookies[selectedBooru!.baseURL!] ?? []);",
    "selectedBooruCookies.addAll(globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host] ?? []);",
    'cookie-cleaner-read-host-key',
)
replace_once(
    network,
    "globalWindowsCookies[selectedBooru!.baseURL!]?.remove(cookie);",
    "globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host]?.remove(cookie);",
    'cookie-cleaner-delete-host-key',
)
replace_once(
    network,
    "globalWindowsCookies[selectedBooru!.baseURL!]?.clear();",
    "globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host]?.clear();",
    'cookie-cleaner-clear-host-key',
)

# Guard the exact bug class this patch fixes.
tools_text = tools.read_text(encoding='utf-8')
network_text = network.read_text(encoding='utf-8')
required = {
    'persistent WebView2 read': 'persistentCookies = await cookieManager.getCookies(url: webUri)' in tools_text,
    'cookie bridge diagnostic': 'COOKIE_BRIDGE_READ' in tools_text,
    'memory map upsert': 'globalWindowsCookies.putIfAbsent' in tools_text,
    'network page host-key read': 'globalWindowsCookies[WebUri(selectedBooru!.baseURL!).host]' in network_text,
}
for label, ok in required.items():
    if not ok:
        raise SystemExit(f'V9 guard failed: {label}')

if 'globalWindowsCookies[selectedBooru!.baseURL!]' in network_text:
    raise SystemExit('V9 guard failed: URL-string cookie map key remains in NetworkPage')

print('WINDOWS_WEBVIEW2_PERSISTENT_COOKIE_READ=PASS')
print('WINDOWS_COOKIE_MEMORY_UPSERT=PASS')
print('WINDOWS_COOKIE_CLEANER_HOST_KEYS=PASS')
print('V9_PATCH=PASS')
