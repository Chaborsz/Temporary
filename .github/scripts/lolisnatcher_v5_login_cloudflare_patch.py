from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count} in {p}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED {label}: {p}")


# ---------------------------------------------------------------------------
# WebView: on Windows use WebView2's native UA instead of the app UA.
# Cloudflare/Turnstile are known to reject or loop when a WebView is given a
# custom UA that does not match the browser's real client hints/fingerprint.
# ---------------------------------------------------------------------------
webview = "lib/src/widgets/webview/webview_page.dart"
replace_once(
    webview,
    "WebViewEnvironment? webViewEnvironment;\nMap<String, List<Cookie>> globalWindowsCookies = {};\n",
    "WebViewEnvironment? webViewEnvironment;\nMap<String, List<Cookie>> globalWindowsCookies = {};\nString? windowsWebViewUserAgent;\n",
    "windows-native-user-agent-state",
)

replace_once(
    webview,
    "      userAgent: widget.userAgent ?? Tools.browserUserAgent,\n      mediaPlaybackRequiresUserGesture: false,\n      javaScriptEnabled: true,\n      cacheEnabled: false,\n",
    "      // On Windows leave UA unset so WebView2 sends its real browser UA and matching client hints.\n      userAgent: Platform.isWindows ? null : (widget.userAgent ?? Tools.browserUserAgent),\n      mediaPlaybackRequiresUserGesture: false,\n      javaScriptEnabled: true,\n      cacheEnabled: Platform.isWindows ? true : false,\n      domStorageEnabled: true,\n",
    "windows-native-webview-user-agent-and-storage",
)

replace_once(
    webview,
    "      globalWindowsCookies[uri.host]!.addAll(cookies);\n\n      setState(() {});\n",
    "      globalWindowsCookies[uri.host]!.addAll(cookies);\n",
    "cookie-snapshot-without-setstate",
)

replace_once(
    webview,
    """              onWebViewCreated: (webViewController) {
                if (!controller.isCompleted) {
                  controller.complete(webViewController);
                }
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'CREATED url=${widget.initialUrl}',
                  ),
                );
""",
    """              onWebViewCreated: (webViewController) {
                if (!controller.isCompleted) {
                  controller.complete(webViewController);
                }
                if (Platform.isWindows) {
                  unawaited(() async {
                    try {
                      final Object? rawUserAgent = await webViewController.evaluateJavascript(
                        source: 'navigator.userAgent;',
                      );
                      final String nativeUserAgent = rawUserAgent?.toString().replaceAll('"', '').trim() ?? '';
                      if (nativeUserAgent.isNotEmpty) {
                        windowsWebViewUserAgent = nativeUserAgent;
                        await appendWindowsWebViewDiagnostic('NATIVE_UA $nativeUserAgent');
                      }
                    } catch (e) {
                      await appendWindowsWebViewDiagnostic('NATIVE_UA_ERROR $e');
                    }
                  }());
                }
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'CREATED url=${widget.initialUrl}',
                  ),
                );
""",
    "capture-native-webview2-user-agent",
)

replace_once(
    webview,
    """              onLoadStop: (controller, url) {
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'LOAD_STOP url=${url?.toString() ?? widget.initialUrl}',
                  ),
                );
                setState(() {
                  loadingPercentage = 100;
                  saveCookiesOnWidnows(controller, url);
                });
                widget.onLoadStop?.call(context, controller, url);
              },
""",
    """              onLoadStop: (controller, url) {
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'LOAD_STOP url=${url?.toString() ?? widget.initialUrl}',
                  ),
                );
                unawaited(saveCookiesOnWidnows(controller, url));
                if (mounted) {
                  setState(() {
                    loadingPercentage = 100;
                  });
                }
                widget.onLoadStop?.call(context, controller, url);
              },
""",
    "save-windows-cookies-outside-setstate",
)

replace_once(
    webview,
    """              onReceivedError: (controller, request, error) {
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'LOAD_ERROR url=${request.url} type=${error.type} description=${error.description}',
                  ),
                );
              },
""",
    """              onReceivedError: (controller, request, error) {
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'LOAD_ERROR url=${request.url} type=${error.type} description=${error.description}',
                  ),
                );
              },
              onConsoleMessage: (controller, consoleMessage) {
                if (!Platform.isWindows) {
                  return;
                }
                final String message = consoleMessage.message;
                final String lower = message.toLowerCase();
                if (lower.contains('cloudflare') ||
                    lower.contains('turnstile') ||
                    lower.contains('challenge') ||
                    lower.contains('error') ||
                    lower.contains('failed')) {
                  unawaited(
                    appendWindowsWebViewDiagnostic(
                      'CONSOLE level=${consoleMessage.messageLevel} message=$message',
                    ),
                  );
                }
              },
""",
    "cloudflare-console-diagnostics",
)

replace_once(
    webview,
    """    if (controller.isCompleted) {
      controller.future.then((controller) => controller.dispose());
    }
""",
    """    if (controller.isCompleted) {
      unawaited(
        controller.future.then((webViewController) async {
          try {
            final WebUri? url = await webViewController.getUrl();
            await saveCookiesOnWidnows(webViewController, url);
          } catch (_) {}
          await webViewController.dispose();
        }),
      );
    }
""",
    "save-login-cookies-before-webview-dispose",
)

# ---------------------------------------------------------------------------
# Cookie bridge + challenge detection.
# ---------------------------------------------------------------------------
tools = "lib/src/utils/tools.dart"
replace_once(
    tools,
    """  static String get browserUserAgent {
    return (isTestMode || SettingsHandler.instance.customUserAgent.isEmpty)
        ? appUserAgent
        : SettingsHandler.instance.customUserAgent;
  }
""",
    """  static String get browserUserAgent {
    if (Platform.isWindows && windowsWebViewUserAgent?.trim().isNotEmpty == true) {
      return windowsWebViewUserAgent!.trim();
    }
    return (isTestMode || SettingsHandler.instance.customUserAgent.isEmpty)
        ? appUserAgent
        : SettingsHandler.instance.customUserAgent;
  }
""",
    "reuse-native-webview-user-agent-for-api",
)

replace_once(
    tools,
    """  static Future<bool> checkForCaptcha(Response? response, Uri uri, {String? customUserAgent}) async {
""",
    """  static bool hasCloudflareChallenge(Response? response) {
    if (response == null) {
      return false;
    }

    final String mitigated = response.headers.value('cf-mitigated')?.trim().toLowerCase() ?? '';
    if (mitigated == 'challenge') {
      return true;
    }

    final String contentType = response.headers.value('content-type')?.toLowerCase() ?? '';
    if (!contentType.contains('text/html')) {
      return false;
    }

    final String content = response.data?.toString().toLowerCase() ?? '';
    const markers = <String>[
      '/cdn-cgi/challenge-platform/',
      'cf-chl-',
      'cf-turnstile',
      'challenges.cloudflare.com',
      'window._cf_chl_opt',
      'verifying you are human',
      'just a moment',
    ];
    return markers.any(content.contains);
  }

  static Future<bool> checkForCaptcha(Response? response, Uri uri, {String? customUserAgent}) async {
""",
    "modern-cloudflare-challenge-detector",
)

replace_once(
    tools,
    """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data.toString() ?? '');

    if (PlatformExt.hasWebviewSupport &&
        ContentPolicy.canOpenWebview &&
        (response?.statusCode == HttpStatus.forbidden ||
            response?.statusCode == HttpStatus.serviceUnavailable ||
            hasCaptchaContent)) {
""",
    """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data.toString() ?? '');
    final bool cloudflareChallenge = hasCloudflareChallenge(response);
    final int? statusCode = response?.statusCode;
    final bool challengeStatus = statusCode == HttpStatus.forbidden ||
        statusCode == HttpStatus.tooManyRequests ||
        statusCode == HttpStatus.serviceUnavailable;

    if (PlatformExt.hasWebviewSupport &&
        ContentPolicy.canOpenWebview &&
        (cloudflareChallenge || challengeStatus || hasCaptchaContent)) {
      if (Platform.isWindows) {
        await appendWindowsWebViewDiagnostic(
          'CAPTCHA_DETECTED host=$host status=$statusCode cfMitigated=${response?.headers.value('cf-mitigated')} '
          'cloudflare=$cloudflareChallenge known=$hasCaptchaContent',
        );
      }
""",
    "detect-current-cloudflare-challenges",
)

replace_once(
    tools,
    """      await Navigator.push(
        NavigationHandler.instance.navContext,
        MaterialPageRoute(
""",
    """      await Navigator.of(
        NavigationHandler.instance.navContext,
        rootNavigator: true,
      ).push(
        MaterialPageRoute(
""",
    "root-navigator-for-automatic-challenge",
)

replace_once(
    tools,
    """        if (Platform.isWindows) {
          cookies.addAll(globalWindowsCookies[WebUri(uri).host] ?? []);
        } else {
          cookies = await cookieManager.getCookies(url: WebUri(uri));
        }
""",
    """        if (Platform.isWindows) {
          final WebUri webUri = WebUri(uri);
          // Read the real WebView2 cookie store so login/cf_clearance survives
          // WebView closure and application restarts. Keep the in-memory map as
          // a fallback for plugin edge cases.
          cookies = await cookieManager.getCookies(url: webUri);
          if (cookies.isNotEmpty) {
            globalWindowsCookies[webUri.host] = List<Cookie>.from(cookies);
          } else {
            cookies.addAll(globalWindowsCookies[webUri.host] ?? []);
          }
        } else {
          cookies = await cookieManager.getCookies(url: WebUri(uri));
        }
""",
    "read-persistent-webview2-cookie-store",
)

replace_once(
    tools,
    """          if (Platform.isWindows) {
            globalWindowsCookies[WebUri(uri).host]?.add(cookie);
          }
""",
    """          if (Platform.isWindows) {
            final String host = WebUri(uri).host;
            final List<Cookie> bucket = globalWindowsCookies.putIfAbsent(host, () => <Cookie>[]);
            bucket.removeWhere((oldCookie) => oldCookie.name == cookie.name);
            bucket.add(cookie);
          }
""",
    "initialize-and-update-windows-cookie-cache",
)

# Retried API request must use the UA that solved the challenge on Windows.
dio = "lib/src/utils/dio_network.dart"
old_headers = """          final headers = {
            ...response.requestOptions.headers,
            'Cookie': '${oldCookie.replaceAll('cf_clearance', 'cf_clearance_old')} $newCookie'.trim(),
            Tools.captchaCheckHeader: 'done',
          };
"""
new_headers = """          final headers = {
            ...response.requestOptions.headers,
            'Cookie': '${oldCookie.replaceAll('cf_clearance', 'cf_clearance_old')} $newCookie'.trim(),
            'User-Agent': Tools.browserUserAgent,
            Tools.captchaCheckHeader: 'done',
          };
"""
replace_once(dio, old_headers, new_headers, "retry-response-with-solved-webview-user-agent")

old_error_headers = """          final headers = {
            ...error.requestOptions.headers,
            'Cookie': '${oldCookie.replaceAll('cf_clearance', 'cf_clearance_old')} $newCookie'.trim(),
            Tools.captchaCheckHeader: 'done',
          };
"""
new_error_headers = """          final headers = {
            ...error.requestOptions.headers,
            'Cookie': '${oldCookie.replaceAll('cf_clearance', 'cf_clearance_old')} $newCookie'.trim(),
            'User-Agent': Tools.browserUserAgent,
            Tools.captchaCheckHeader: 'done',
          };
"""
replace_once(dio, old_error_headers, new_error_headers, "retry-error-with-solved-webview-user-agent")

# ---------------------------------------------------------------------------
# Booru editor: this is the path used while ADDING a new login-protected booru.
# v4 only hardened the WebView button on the already-added booru page.
# ---------------------------------------------------------------------------
booru_edit = "lib/src/pages/settings/booru_edit_page.dart"
replace_once(
    booru_edit,
    """                action: () {
                  if (booruURLController.text.isNotEmpty) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => InAppWebviewView(
                          initialUrl: booruURLController.text,
                        ),
                      ),
                    );
                  }
                },
""",
    r"""                action: () async {
                  final String rawUrl = booruURLController.text.trim();
                  if (rawUrl.isEmpty) {
                    return;
                  }

                  String targetUrl = rawUrl;
                  final Uri? parsed = Uri.tryParse(targetUrl);
                  if (parsed == null || parsed.scheme.isEmpty) {
                    targetUrl = 'https://$targetUrl';
                  }

                  await appendWindowsWebViewDiagnostic(
                    'EDITOR_OPEN_REQUEST url=$targetUrl type=${selectedBooruType.name}',
                  );
                  if (!context.mounted) {
                    return;
                  }

                  try {
                    await Navigator.of(context, rootNavigator: true).push(
                      MaterialPageRoute(
                        builder: (_) => InAppWebviewView(initialUrl: targetUrl),
                      ),
                    );
                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_CLOSED url=$targetUrl',
                    );
                  } catch (e, s) {
                    await appendWindowsWebViewDiagnostic(
                      'EDITOR_ROUTE_ERROR url=$targetUrl error=$e',
                    );
                    Logger.Inst().log(
                      e.toString(),
                      'BooruEdit',
                      'openWebView',
                      LogTypes.exception,
                      s: s,
                    );
                    if (!context.mounted) {
                      return;
                    }
                    await showDialog<void>(
                      context: context,
                      builder: (_) => AlertDialog(
                        title: const Text('Open WebView'),
                        content: SelectableText(e.toString()),
                      ),
                    );
                  }
                },
""",
    "harden-new-booru-editor-webview-route",
)

replace_once(
    booru_edit,
    """          withCaptchaCheck: false,
""",
    """          withCaptchaCheck: withCaptchaCheck,
""",
    "allow-captcha-during-booru-autodetect",
)

# Guards
checks = {
    "native UA state": "windowsWebViewUserAgent" in Path(webview).read_text(encoding="utf-8"),
    "native UA used by Windows WebView": "userAgent: Platform.isWindows ? null" in Path(webview).read_text(encoding="utf-8"),
    "cf-mitigated detection": "cf-mitigated" in Path(tools).read_text(encoding="utf-8"),
    "persistent Windows cookies": "cookieManager.getCookies(url: webUri)" in Path(tools).read_text(encoding="utf-8"),
    "retry UA sync": "'User-Agent': Tools.browserUserAgent" in Path(dio).read_text(encoding="utf-8"),
    "editor root route": "EDITOR_OPEN_REQUEST" in Path(booru_edit).read_text(encoding="utf-8"),
    "autodetect captcha": "withCaptchaCheck: withCaptchaCheck" in Path(booru_edit).read_text(encoding="utf-8"),
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f"V5 guard failed: {label}")

print("V5_NATIVE_WEBVIEW2_UA=PASS")
print("V5_CLOUDFLARE_CF_MITIGATED=PASS")
print("V5_WEBVIEW2_PERSISTENT_COOKIES=PASS")
print("V5_NEW_BOORU_EDITOR_WEBVIEW=PASS")
print("V5_AUTODETECT_CAPTCHA=PASS")
print("V5_PATCH=PASS")
