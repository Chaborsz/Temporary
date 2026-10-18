from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


def splice_once(path, start_marker, end_marker, replacement, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f'{label}: start marker not found in {p}')
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f'{label}: end marker not found in {p}')
    end += len(end_marker)
    p.write_text(text[:start] + replacement + text[end:], encoding='utf-8')
    print(f'PATCHED {label}: {p}')


webview = Path('lib/src/widgets/webview/webview_page.dart')
text = webview.read_text(encoding='utf-8')

# Add a Windows-only native InAppBrowser implementation.  Unlike the embedded
# InAppWebView widget, InAppBrowser uses a normal CoreWebView2Controller in its
# own HWND and does not depend on the GraphicsCapture/composition texture path
# that hangs before onWebViewCreated on affected Windows machines.
anchor = "Map<String, List<Cookie>> globalWindowsCookies = {};\nString? windowsWebViewUserAgent;\n"
if text.count(anchor) != 1:
    raise SystemExit('native-browser-helper: global anchor changed')
helper = r'''Map<String, List<Cookie>> globalWindowsCookies = {};
String? windowsWebViewUserAgent;

class _PortableWindowsInAppBrowser extends InAppBrowser {
  _PortableWindowsInAppBrowser({
    required this.closed,
    required this.onNativeLoadStop,
  }) : super(webViewEnvironment: webViewEnvironment);

  final Completer<void> closed;
  final Future<bool> Function(InAppWebViewController controller, WebUri? url)? onNativeLoadStop;

  @override
  void onBrowserCreated() {
    unawaited(appendWindowsWebViewDiagnostic('NATIVE_BROWSER_CREATED id=$id'));
  }

  @override
  void onLoadStart(WebUri? url) {
    unawaited(
      appendWindowsWebViewDiagnostic(
        'NATIVE_BROWSER_LOAD_START url=${url?.toString() ?? ''}',
      ),
    );
  }

  @override
  void onLoadStop(WebUri? url) {
    unawaited(() async {
      await appendWindowsWebViewDiagnostic(
        'NATIVE_BROWSER_LOAD_STOP url=${url?.toString() ?? ''}',
      );
      final controller = webViewController;
      if (controller == null) {
        await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_NO_CONTROLLER');
        return;
      }
      try {
        final Object? rawUserAgent = await controller.evaluateJavascript(
          source: 'navigator.userAgent;',
        );
        final String nativeUserAgent = rawUserAgent?.toString().replaceAll('"', '').trim() ?? '';
        if (nativeUserAgent.isNotEmpty) {
          windowsWebViewUserAgent = nativeUserAgent;
          await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_UA $nativeUserAgent');
        }
      } catch (e) {
        await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_UA_ERROR $e');
      }
      final WebUri effectiveUrl = url ?? WebUri('about:blank');
      if (url != null) {
        try {
          final cookies = await CookieManager.instance(
            webViewEnvironment: webViewEnvironment,
          ).getCookies(url: effectiveUrl, webViewController: controller);
          if (cookies.isNotEmpty) {
            globalWindowsCookies[effectiveUrl.host] = List<Cookie>.from(cookies);
          }
          await appendWindowsWebViewDiagnostic(
            'NATIVE_BROWSER_COOKIES host=${effectiveUrl.host} count=${cookies.length}',
          );
        } catch (e) {
          await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_COOKIE_ERROR $e');
        }
      }
      final shouldClose = await onNativeLoadStop?.call(controller, url) ?? false;
      if (shouldClose && isOpened()) {
        await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_AUTO_CLOSE');
        await close();
      }
    }());
  }

  @override
  void onReceivedError(WebResourceRequest request, WebResourceError error) {
    unawaited(
      appendWindowsWebViewDiagnostic(
        'NATIVE_BROWSER_ERROR url=${request.url} type=${error.type} description=${error.description}',
      ),
    );
  }

  @override
  void onConsoleMessage(ConsoleMessage consoleMessage) {
    final String message = consoleMessage.message;
    final String lower = message.toLowerCase();
    if (lower.contains('challenge') ||
        lower.contains('cloudflare') ||
        lower.contains('turnstile') ||
        lower.contains('error') ||
        lower.contains('failed')) {
      unawaited(
        appendWindowsWebViewDiagnostic(
          'NATIVE_BROWSER_CONSOLE level=${consoleMessage.messageLevel} message=$message',
        ),
      );
    }
  }

  @override
  void onExit() {
    unawaited(appendWindowsWebViewDiagnostic('NATIVE_BROWSER_EXIT'));
    if (!closed.isCompleted) {
      closed.complete();
    }
  }
}

Future<void> openPortableWindowsNativeBrowser(
  String initialUrl, {
  Future<bool> Function(InAppWebViewController controller, WebUri? url)? onLoadStop,
}) async {
  if (!Platform.isWindows) {
    throw UnsupportedError('Native Windows browser is only available on Windows');
  }
  final Completer<void> closed = Completer<void>();
  final browser = _PortableWindowsInAppBrowser(
    closed: closed,
    onNativeLoadStop: onLoadStop,
  );
  await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_OPEN url=$initialUrl');
  try {
    await browser.openUrlRequest(
      urlRequest: URLRequest(url: WebUri(initialUrl)),
      settings: InAppBrowserClassSettings(
        webViewSettings: InAppWebViewSettings(
          userAgent: null,
          javaScriptEnabled: true,
          cacheEnabled: true,
          domStorageEnabled: true,
          thirdPartyCookiesEnabled: true,
          javaScriptCanOpenWindowsAutomatically: true,
          mediaPlaybackRequiresUserGesture: false,
        ),
      ),
    );
    await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_OPENED url=$initialUrl');
    await closed.future;
  } catch (e, s) {
    await appendWindowsWebViewDiagnostic('NATIVE_BROWSER_OPEN_ERROR url=$initialUrl error=$e');
    Logger.Inst().log(
      e.toString(),
      'WebViewPage',
      'openPortableWindowsNativeBrowser',
      LogTypes.exception,
      s: s,
    );
    rethrow;
  } finally {
    browser.dispose();
  }
}
'''
text = text.replace(anchor, helper, 1)
webview.write_text(text, encoding='utf-8')
print('PATCHED native-windows-inappbrowser-helper:', webview)

# Route the already-added booru Open WebView button through the native browser
# on Windows. Other platforms keep the existing Flutter route.
booru_page = Path('lib/src/pages/settings/booru_page.dart')
booru_text = booru_page.read_text(encoding='utf-8')
old = """          try {
            await Navigator.of(context, rootNavigator: true).push(
              MaterialPageRoute(
                builder: (_) => InAppWebviewView(initialUrl: targetUrl),
              ),
            );
            await appendWindowsWebViewDiagnostic(
              'ROUTE_CLOSED url=$targetUrl',
            );
"""
new = """          try {
            if (Platform.isWindows) {
              await openPortableWindowsNativeBrowser(targetUrl);
            } else {
              await Navigator.of(context, rootNavigator: true).push(
                MaterialPageRoute(
                  builder: (_) => InAppWebviewView(initialUrl: targetUrl),
                ),
              );
            }
            await appendWindowsWebViewDiagnostic(
              'ROUTE_CLOSED url=$targetUrl',
            );
"""
if booru_text.count(old) != 1:
    raise SystemExit(f'booru-native-browser-route: expected 1 match, found {booru_text.count(old)}')
booru_page.write_text(booru_text.replace(old, new, 1), encoding='utf-8')
print('PATCHED booru-native-browser-route:', booru_page)

# Route the new-booru editor through the same native browser on Windows.
booru_edit = Path('lib/src/pages/settings/booru_edit_page.dart')
edit_text = booru_edit.read_text(encoding='utf-8')
old = """                  try {
                    await Navigator.of(context, rootNavigator: true).push(
                      MaterialPageRoute(
                        builder: (_) => InAppWebviewView(initialUrl: targetUrl),
                      ),
                    );
                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_CLOSED url=$targetUrl',
                    );
"""
new = """                  try {
                    if (Platform.isWindows) {
                      await openPortableWindowsNativeBrowser(targetUrl);
                    } else {
                      await Navigator.of(context, rootNavigator: true).push(
                        MaterialPageRoute(
                          builder: (_) => InAppWebviewView(initialUrl: targetUrl),
                        ),
                      );
                    }
                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_CLOSED url=$targetUrl',
                    );
"""
if edit_text.count(old) != 1:
    raise SystemExit(f'editor-native-browser-route: expected 1 match, found {edit_text.count(old)}')
booru_edit.write_text(edit_text.replace(old, new, 1), encoding='utf-8')
print('PATCHED editor-native-browser-route:', booru_edit)

# Replace the Windows automatic challenge route with the native browser.  The
# callback evaluates the real page after each navigation and closes the native
# window only when the actual challenge markers have disappeared. Cloudflare
# still requires cf_clearance; Nginx-Lua/processChallenge does not.
tools = Path('lib/src/utils/tools.dart')
tools_text = tools.read_text(encoding='utf-8')
start_marker = "      bool userDecidedToStay = false;\n      try {\n"
end_marker = "      captchaScreenActive = false;\n      return true;\n"
replacement = r'''      bool userDecidedToStay = false;
      try {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_NATIVE_BROWSER_PUSH engine=$challengeEngine url=${uri.scheme}://$host',
          );
          await openPortableWindowsNativeBrowser(
            '${uri.scheme}://$host${uri.hasPort && uri.port != 80 ? ':${uri.port}' : ''}',
            onLoadStop: (controller, url) async {
              if (url == null) {
                return false;
              }
              await Future.delayed(const Duration(milliseconds: 500));
              final CookieManager cookieManager = CookieManager.instance(
                webViewEnvironment: webViewEnvironment,
              );
              final List<Cookie> cookies = await cookieManager.getCookies(
                url: url,
                webViewController: controller,
              );
              if (cookies.isNotEmpty) {
                globalWindowsCookies[url.host] = List<Cookie>.from(cookies);
              }
              final bool hasClearanceCookie = cookies.any((c) => c.name == 'cf_clearance');
              final String? htmlContent = await controller.evaluateJavascript(
                source: 'window.document.documentElement.outerHTML;',
              );
              if (htmlContent == null) {
                return false;
              }
              final String htmlLower = htmlContent.toLowerCase();
              final bool isCloudflareChallengeActive =
                  htmlLower.contains('/cdn-cgi/challenge-platform/') ||
                  htmlLower.contains('id="cf-challenge-') ||
                  htmlLower.contains('cf-browser-verification') ||
                  htmlLower.contains('cf-turnstile') ||
                  htmlLower.contains('window._cf_chl_opt');
              final bool isKnownCaptchaRunning = hasCaptchaStrings(url.host, htmlContent);
              final bool cloudflareSolved = cloudflareChallenge &&
                  hasClearanceCookie &&
                  !isCloudflareChallengeActive &&
                  !isKnownCaptchaRunning;
              final bool knownChallengeSolved = !cloudflareChallenge &&
                  (nginxAntiDdosChallenge || knownNonCloudflareChallenge) &&
                  !isKnownCaptchaRunning;
              final bool challengeSolved = cloudflareSolved || knownChallengeSolved;
              await appendWindowsWebViewDiagnostic(
                'NATIVE_CHALLENGE_STATE engine=$challengeEngine url=$url cookies=${cookies.length} '
                'cfClearance=$hasClearanceCookie cfActive=$isCloudflareChallengeActive '
                'knownActive=$isKnownCaptchaRunning solved=$challengeSolved',
              );
              return challengeSolved;
            },
          );
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_NATIVE_BROWSER_POP engine=$challengeEngine',
          );
        } else {
          await Navigator.of(
            NavigationHandler.instance.navContext,
            rootNavigator: true,
          ).push(
            MaterialPageRoute(
              builder: (context) => InAppWebviewView(
                initialUrl: '${uri.scheme}://$host${uri.hasPort && uri.port != 80 ? ':${uri.port}' : ''}',
                userAgent: customUserAgent,
                title: context.loc.webview.captcha,
                subtitle: context.loc.webview.captchaCheckDescription,
                onLoadStop: (context, controller, url) async {
                  if (url == null) return;
                  await Future.delayed(const Duration(milliseconds: 500));
                  final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
                  final List<Cookie> cookies = await cookieManager.getCookies(url: url);
                  final bool hasClearanceCookie = cookies.any((c) => c.name == 'cf_clearance');
                  final String? htmlContent = await controller.evaluateJavascript(
                    source: 'window.document.documentElement.outerHTML;',
                  );
                  if (htmlContent == null) return;
                  final String htmlLower = htmlContent.toLowerCase();
                  final bool isCloudflareChallengeActive =
                      htmlLower.contains('/cdn-cgi/challenge-platform/') ||
                      htmlLower.contains('id="cf-challenge-') ||
                      htmlLower.contains('cf-browser-verification') ||
                      htmlLower.contains('cf-turnstile') ||
                      htmlLower.contains('window._cf_chl_opt');
                  final bool isKnownCaptchaRunning = hasCaptchaStrings(url.host, htmlContent);
                  final bool cloudflareSolved = cloudflareChallenge &&
                      hasClearanceCookie &&
                      !isCloudflareChallengeActive &&
                      !isKnownCaptchaRunning;
                  final bool knownChallengeSolved = !cloudflareChallenge &&
                      (nginxAntiDdosChallenge || knownNonCloudflareChallenge) &&
                      !isKnownCaptchaRunning &&
                      cookies.isNotEmpty;
                  final bool challengeSolved = cloudflareSolved || knownChallengeSolved;
                  if (context.mounted && challengeSolved && !userDecidedToStay) {
                    final bool res = await showTimedLeaveDialog(
                      context,
                      title: context.loc.webview.captchaCompleted,
                      icon: const Icon(Icons.thumb_up_alt_rounded),
                      duration: const Duration(seconds: 4),
                    );
                    if (res) {
                      Navigator.of(context).pop();
                    } else {
                      userDecidedToStay = true;
                    }
                  }
                },
              ),
            ),
          );
        }
      } catch (e, s) {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_NATIVE_BROWSER_ERROR engine=$challengeEngine error=$e',
          );
        }
        Logger.Inst().log(
          e.toString(),
          'Tools',
          'checkForCaptchaRoute',
          LogTypes.exception,
          s: s,
        );
        captchaScreenActive = false;
        return false;
      }
      captchaScreenActive = false;
      return true;
'''
start = tools_text.find(start_marker)
if start < 0:
    raise SystemExit('challenge-native-browser: start marker not found')
end = tools_text.find(end_marker, start)
if end < 0:
    raise SystemExit('challenge-native-browser: end marker not found')
end += len(end_marker)
tools.write_text(tools_text[:start] + replacement + tools_text[end:], encoding='utf-8')
print('PATCHED challenge-native-browser:', tools)

# Guards
checks = {
    'native browser helper': 'openPortableWindowsNativeBrowser' in webview.read_text(encoding='utf-8'),
    'native browser creation diagnostic': 'NATIVE_BROWSER_CREATED' in webview.read_text(encoding='utf-8'),
    'booru route native browser': 'if (Platform.isWindows)' in booru_page.read_text(encoding='utf-8') and 'openPortableWindowsNativeBrowser(targetUrl)' in booru_page.read_text(encoding='utf-8'),
    'editor route native browser': 'openPortableWindowsNativeBrowser(targetUrl)' in booru_edit.read_text(encoding='utf-8'),
    'challenge native browser': 'CHALLENGE_NATIVE_BROWSER_PUSH' in tools.read_text(encoding='utf-8'),
    'native challenge state': 'NATIVE_CHALLENGE_STATE' in tools.read_text(encoding='utf-8'),
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V7 guard failed: {label}')

print('V7_NATIVE_WINDOWS_INAPPBROWSER=PASS')
print('V7_EMBEDDED_COMPOSITION_BYPASS=PASS')
print('V7_CHALLENGE_NATIVE_BROWSER=PASS')
print('V7_PATCH=PASS')