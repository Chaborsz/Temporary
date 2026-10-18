from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count} in {p}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED {label}: {p}")


webview = "lib/src/widgets/webview/webview_page.dart"
tools = "lib/src/utils/tools.dart"

# ---------------------------------------------------------------------------
# Windows WebView2: do not rely on initialUrlRequest being dispatched before
# the Windows platform view/controller is fully ready.  Create the view first,
# then explicitly navigate once the controller exists.  This also gives the
# diagnostics a precise CREATED -> NAVIGATE -> LOAD_START sequence.
# ---------------------------------------------------------------------------
replace_once(
    webview,
    "              initialUrlRequest: URLRequest(url: WebUri(widget.initialUrl)),\n",
    "              initialUrlRequest: Platform.isWindows ? null : URLRequest(url: WebUri(widget.initialUrl)),\n",
    "windows-explicit-navigation-instead-of-initial-request",
)

old_windows_created = """                if (Platform.isWindows) {
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
"""
new_windows_created = """                if (Platform.isWindows) {
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

                    try {
                      final WebUri target = WebUri(widget.initialUrl);
                      await appendWindowsWebViewDiagnostic('NAVIGATE_EXPLICIT url=$target');
                      await webViewController.loadUrl(
                        urlRequest: URLRequest(url: target),
                      );
                    } catch (e, s) {
                      await appendWindowsWebViewDiagnostic(
                        'NAVIGATE_EXPLICIT_ERROR url=${widget.initialUrl} error=$e',
                      );
                      Logger.Inst().log(
                        e.toString(),
                        'WebViewPage',
                        'explicitWindowsNavigation',
                        LogTypes.exception,
                        s: s,
                      );
                    }
                  }());
                }
"""
replace_once(
    webview,
    old_windows_created,
    new_windows_created,
    "windows-explicit-navigation-after-controller-created",
)

replace_once(
    webview,
    """              onLoadStart: (controller, url) {
                setState(() {
                  loadingPercentage = 0;
                });
              },
""",
    """              onLoadStart: (controller, url) {
                if (Platform.isWindows) {
                  unawaited(
                    appendWindowsWebViewDiagnostic(
                      'LOAD_START url=${url?.toString() ?? widget.initialUrl}',
                    ),
                  );
                }
                if (mounted) {
                  setState(() {
                    loadingPercentage = 0;
                  });
                }
              },
""",
    "diagnose-webview-load-start",
)

replace_once(
    webview,
    """              onUpdateVisitedHistory: (controller, url, isReload) {
                setState(() {
                  loadingPercentage = 0;
                });
              },
""",
    """              onUpdateVisitedHistory: (controller, url, isReload) {
                if (Platform.isWindows) {
                  unawaited(
                    appendWindowsWebViewDiagnostic(
                      'HISTORY url=${url?.toString() ?? ''} reload=$isReload',
                    ),
                  );
                }
                if (mounted) {
                  setState(() {
                    loadingPercentage = 0;
                  });
                }
              },
""",
    "diagnose-webview-history",
)

# ---------------------------------------------------------------------------
# Challenge engine classification.
# AllTheFallen uses Conor McKnight's Nginx-Lua-Anti-DDoS JavaScript puzzle.
# It deliberately does NOT use Cloudflare and therefore does not issue a
# cf_clearance cookie.  LoliSnatcher already knows its HTML marker
# (processChallenge), but the completion logic incorrectly required
# cf_clearance for every challenge.
# ---------------------------------------------------------------------------
replace_once(
    tools,
    """  static Future<bool> checkForCaptcha(Response? response, Uri uri, {String? customUserAgent}) async {
""",
    """  static bool hasNginxAntiDdosChallenge(Response? response, String host) {
    if (response == null) {
      return false;
    }
    final String antiDdosHeader = response.headers.value('x-anti-ddos')?.toLowerCase() ?? '';
    if (antiDdosHeader.contains('conor mcknight')) {
      return true;
    }
    return host.contains('booru.allthefallen.moe') &&
        hasCaptchaStrings(host, response.data?.toString() ?? '');
  }

  static Future<bool> checkForCaptcha(Response? response, Uri uri, {String? customUserAgent}) async {
""",
    "detect-nginx-lua-antiddos-engine",
)

old_detection = """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data.toString() ?? '');
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
"""
new_detection = """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data.toString() ?? '');
    final bool cloudflareChallenge = hasCloudflareChallenge(response);
    final bool nginxAntiDdosChallenge = hasNginxAntiDdosChallenge(response, host);
    final bool knownNonCloudflareChallenge = hasCaptchaContent && !cloudflareChallenge;
    final int? statusCode = response?.statusCode;
    final bool challengeStatus = statusCode == HttpStatus.forbidden ||
        statusCode == HttpStatus.tooManyRequests ||
        statusCode == HttpStatus.serviceUnavailable;
    final String challengeEngine = cloudflareChallenge
        ? 'cloudflare'
        : (nginxAntiDdosChallenge ? 'nginx-lua-antiddos' : (knownNonCloudflareChallenge ? 'known-non-cloudflare' : 'http-status'));

    if (PlatformExt.hasWebviewSupport &&
        ContentPolicy.canOpenWebview &&
        (cloudflareChallenge || nginxAntiDdosChallenge || challengeStatus || hasCaptchaContent)) {
      if (Platform.isWindows) {
        await appendWindowsWebViewDiagnostic(
          'CAPTCHA_DETECTED host=$host status=$statusCode engine=$challengeEngine '
          'cfMitigated=${response?.headers.value('cf-mitigated')} '
          'xAntiDdos=${response?.headers.value('x-anti-ddos')} '
          'cloudflare=$cloudflareChallenge nginx=$nginxAntiDdosChallenge known=$hasCaptchaContent '
          'request=${response?.requestOptions.uri} real=${response?.realUri}',
        );
      }
"""
replace_once(
    tools,
    old_detection,
    new_detection,
    "classify-cloudflare-vs-nginx-antiddos",
)

old_delete = """      // delete invalid cloudflare cookie
      final webUri = WebUri('${uri.scheme}://$host');
      final bool res =
          await CookieManager.instance(
            webViewEnvironment: webViewEnvironment,
          ).deleteCookie(
            url: webUri,
            name: 'cf_clearance',
          );
      if (!res) {
        Logger.Inst().log(
          'Failed to delete cookie',
          'Tools',
          'checkForCaptcha',
          LogTypes.exception,
          s: StackTrace.current,
        );
      }

      captchaScreenActive = true;
"""
new_delete = """      // cf_clearance belongs to Cloudflare only.  Do not touch it for
      // Nginx-Lua-Anti-DDoS / processChallenge, which authenticates with its
      // own rotating cookies.
      final webUri = WebUri('${uri.scheme}://$host');
      if (cloudflareChallenge) {
        final bool res =
            await CookieManager.instance(
              webViewEnvironment: webViewEnvironment,
            ).deleteCookie(
              url: webUri,
              name: 'cf_clearance',
            );
        if (!res) {
          Logger.Inst().log(
            'Failed to delete Cloudflare cookie',
            'Tools',
            'checkForCaptcha',
            LogTypes.exception,
            s: StackTrace.current,
          );
        }
      }

      captchaScreenActive = true;
"""
replace_once(
    tools,
    old_delete,
    new_delete,
    "do-not-delete-cloudflare-cookie-for-nginx-antiddos",
)

# Add route diagnostics and ensure a failed Navigator push does not leave the
# global captcha lock permanently enabled.
replace_once(
    tools,
    """      await Navigator.of(
        NavigationHandler.instance.navContext,
        rootNavigator: true,
      ).push(
""",
    """      try {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_ROUTE_PUSH engine=$challengeEngine url=${uri.scheme}://$host',
          );
        }
        await Navigator.of(
          NavigationHandler.instance.navContext,
          rootNavigator: true,
        ).push(
""",
    "diagnose-challenge-route-push",
)

old_onload = """              final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
              final List<Cookie> cookies = await cookieManager.getCookies(url: url);
              final bool hasClearanceCookie = [
                ...cookies,
                ...?globalWindowsCookies[url.host],
              ].any((c) => c.name == 'cf_clearance');

              final String? htmlContent = await controller.evaluateJavascript(
                source: 'window.document.documentElement.outerHTML;',
              );

              if (htmlContent == null) return;

              final bool isCloudflareChallengeActive =
                  htmlContent.contains('/cdn-cgi/challenge-platform/') ||
                  htmlContent.contains('id=\"cf-challenge-') ||
                  htmlContent.contains('cf-browser-verification');
              final bool isKnownCaptchaRunning = hasCaptchaStrings(url.host, htmlContent);
              if (context.mounted &&
                  hasClearanceCookie &&
                  !isCloudflareChallengeActive &&
                  !isKnownCaptchaRunning &&
                  !userDecidedToStay) {
"""
new_onload = """              final CookieManager cookieManager = CookieManager.instance(webViewEnvironment: webViewEnvironment);
              final List<Cookie> cookies = Platform.isWindows
                  ? await cookieManager.getCookies(url: url, webViewController: controller)
                  : await cookieManager.getCookies(url: url);
              if (Platform.isWindows && cookies.isNotEmpty) {
                globalWindowsCookies[url.host] = List<Cookie>.from(cookies);
              }
              final bool hasClearanceCookie = [
                ...cookies,
                ...?globalWindowsCookies[url.host],
              ].any((c) => c.name == 'cf_clearance');

              final String? htmlContent = await controller.evaluateJavascript(
                source: 'window.document.documentElement.outerHTML;',
              );

              if (htmlContent == null) return;

              final String htmlLower = htmlContent.toLowerCase();
              final bool isCloudflareChallengeActive =
                  htmlLower.contains('/cdn-cgi/challenge-platform/') ||
                  htmlLower.contains('id=\"cf-challenge-') ||
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

              if (Platform.isWindows) {
                await appendWindowsWebViewDiagnostic(
                  'CHALLENGE_STATE engine=$challengeEngine url=$url cookies=${cookies.length} '
                  'cfClearance=$hasClearanceCookie cfActive=$isCloudflareChallengeActive '
                  'knownActive=$isKnownCaptchaRunning solved=$challengeSolved',
                );
              }

              if (context.mounted && challengeSolved && !userDecidedToStay) {
"""
replace_once(
    tools,
    old_onload,
    new_onload,
    "complete-non-cloudflare-known-challenge-with-its-own-cookies",
)

replace_once(
    tools,
    """      );
      captchaScreenActive = false;
      return true;
""",
    """        );
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_ROUTE_POP engine=$challengeEngine',
          );
        }
      } catch (e, s) {
        if (Platform.isWindows) {
          await appendWindowsWebViewDiagnostic(
            'CHALLENGE_ROUTE_ERROR engine=$challengeEngine error=$e',
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
""",
    "unlock-captcha-state-if-route-fails",
)

# Guards
webview_text = Path(webview).read_text(encoding="utf-8")
tools_text = Path(tools).read_text(encoding="utf-8")
checks = {
    "explicit Windows navigation": "NAVIGATE_EXPLICIT" in webview_text,
    "Windows has no initial URL request": "initialUrlRequest: Platform.isWindows ? null" in webview_text,
    "load-start diagnostics": "LOAD_START" in webview_text,
    "nginx anti-ddos header": "x-anti-ddos" in tools_text,
    "nginx anti-ddos engine": "nginx-lua-antiddos" in tools_text,
    "non-CF completion": "knownChallengeSolved" in tools_text,
    "controller cookie read": "webViewController: controller" in tools_text,
    "challenge state diagnostic": "CHALLENGE_STATE" in tools_text,
    "route error unlock": "CHALLENGE_ROUTE_ERROR" in tools_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f"V6 guard failed: {label}")

print("V6_WINDOWS_EXPLICIT_NAVIGATION=PASS")
print("V6_NGINX_LUA_ANTIDDOS=PASS")
print("V6_NON_CLOUDFLARE_CHALLENGE_COMPLETION=PASS")
print("V6_CHALLENGE_ROUTE_DIAGNOSTICS=PASS")
print("V6_PATCH=PASS")
