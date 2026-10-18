from pathlib import Path

PR2838_COMMIT = "832d6517b50b3b8094d2658800aa84ee5b9294bf"


def replace_once(path: str | Path, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{label}: expected exactly one match, found {count} in {p}"
        )
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED {label}: {p}")


# Keep a normal direct dependency so importing the Windows package is valid,
# then use dependency_overrides to force the full upstream PR #2838 revision.
# This is required because flutter_inappwebview itself declares the Windows
# implementation from hosted pub.dev, and Pub rejects mixed sources unless the
# source change is expressed as an override.
replace_once(
    "pubspec.yaml",
    "  flutter_inappwebview: ^6.2.0-beta.3\n",
    '''  flutter_inappwebview: ^6.2.0-beta.3
  flutter_inappwebview_windows: ^0.7.0-beta.3
''',
    "declare-direct-windows-plugin-dependency",
)
replace_once(
    "pubspec.yaml",
    "dependency_overrides:\n",
    f'''dependency_overrides:
  # Complete Windows fixes from upstream PR #2838.
  flutter_inappwebview_windows:
    git:
      url: https://github.com/pichillilorenzo/flutter_inappwebview.git
      ref: {PR2838_COMMIT}
      path: flutter_inappwebview_windows
''',
    "override-windows-plugin-with-full-pr2838",
)

webview_page = Path("lib/src/widgets/webview/webview_page.dart")
replace_once(
    webview_page,
    "import 'package:flutter_inappwebview/flutter_inappwebview.dart';\n",
    "import 'package:flutter_inappwebview/flutter_inappwebview.dart';\nimport 'package:flutter_inappwebview_windows/flutter_inappwebview_windows.dart';\n",
    "import-windows-webview-failure-api",
)
replace_once(
    webview_page,
    "import 'package:lolisnatcher/src/utils/extensions.dart';\nimport 'package:lolisnatcher/src/utils/tools.dart';\n",
    "import 'package:lolisnatcher/src/utils/extensions.dart';\nimport 'package:lolisnatcher/src/utils/logger.dart';\nimport 'package:lolisnatcher/src/utils/tools.dart';\n",
    "import-webview-logger",
)
replace_once(
    webview_page,
    '''WebViewEnvironment? webViewEnvironment;
Map<String, List<Cookie>> globalWindowsCookies = {};
''',
    r'''WebViewEnvironment? webViewEnvironment;
Map<String, List<Cookie>> globalWindowsCookies = {};

Future<void> appendWindowsWebViewDiagnostic(String message) async {
  if (!Platform.isWindows) {
    return;
  }
  try {
    final File diagnosticFile = File(
      '${File(Platform.resolvedExecutable).parent.path}${Platform.pathSeparator}Data'
      '${Platform.pathSeparator}webview-diagnostic.txt',
    );
    await diagnosticFile.parent.create(recursive: true);
    await diagnosticFile.writeAsString(
      '${DateTime.now().toIso8601String()} $message\n',
      mode: FileMode.append,
      flush: true,
    );
  } catch (_) {
    // Diagnostics must never prevent the WebView page from opening.
  }
}
''',
    "portable-webview-diagnostic-writer",
)
replace_once(
    webview_page,
    '''  final GlobalKey webViewKey = GlobalKey();

  Completer<InAppWebViewController> controller = Completer<InAppWebViewController>();
  late final InAppWebViewSettings settings;

  PullToRefreshController? pullToRefreshController;
  int loadingPercentage = 0;
  bool hideSubtitle = false;
''',
    '''  GlobalKey webViewKey = GlobalKey();

  Completer<InAppWebViewController> controller = Completer<InAppWebViewController>();
  late final InAppWebViewSettings settings;
  StreamSubscription<WindowsWebViewCreationFailure>? windowsFailureSubscription;
  String? windowsCreationError;

  PullToRefreshController? pullToRefreshController;
  int loadingPercentage = 0;
  bool hideSubtitle = false;
''',
    "webview-runtime-diagnostic-state",
)
replace_once(
    webview_page,
    '''      javaScriptCanOpenWindowsAutomatically: true,
    );

    if (PlatformExt.isMobile) {
''',
    '''      javaScriptCanOpenWindowsAutomatically: true,
    );

    if (Platform.isWindows) {
      unawaited(
        appendWindowsWebViewDiagnostic(
          'PAGE_INIT url=${widget.initialUrl} environmentReady=${webViewEnvironment != null}',
        ),
      );
      windowsFailureSubscription = WindowsWebViewCreationFailures.stream.listen((failure) {
        if (failure.creationKey != webViewKey) {
          return;
        }
        final String message = failure.error.toString();
        unawaited(
          appendWindowsWebViewDiagnostic(
            'CREATE_FAILURE url=${failure.requestedUrl ?? widget.initialUrl} error=$message',
          ),
        );
        Logger.Inst().log(
          message,
          'WebViewPage',
          'creation',
          null,
          s: failure.stackTrace,
        );
        if (mounted) {
          setState(() {
            windowsCreationError = message;
            loadingPercentage = 100;
          });
        }
      });
    }

    if (PlatformExt.isMobile) {
''',
    "listen-for-native-webview-creation-failures",
)
replace_once(
    webview_page,
    '''  @override
  void dispose() {
    pullToRefreshController?.dispose();
    controller.future.then((controller) => controller.dispose());
    super.dispose();
  }
''',
    '''  @override
  void dispose() {
    windowsFailureSubscription?.cancel();
    pullToRefreshController?.dispose();
    if (controller.isCompleted) {
      controller.future.then((controller) => controller.dispose());
    }
    super.dispose();
  }
''',
    "safe-webview-dispose-after-creation-failure",
)
replace_once(
    webview_page,
    '''            InAppWebView(
              initialUrlRequest: URLRequest(url: WebUri(widget.initialUrl)),
''',
    '''            InAppWebView(
              key: webViewKey,
              initialUrlRequest: URLRequest(url: WebUri(widget.initialUrl)),
''',
    "pass-webview-creation-key",
)
replace_once(
    webview_page,
    '''              onWebViewCreated: (webViewController) {
                controller.complete(webViewController);
                // webViewController.clearCache();
              },
''',
    '''              onWebViewCreated: (webViewController) {
                if (!controller.isCompleted) {
                  controller.complete(webViewController);
                }
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'CREATED url=${widget.initialUrl}',
                  ),
                );
                if (mounted && windowsCreationError != null) {
                  setState(() {
                    windowsCreationError = null;
                  });
                }
                // webViewController.clearCache();
              },
''',
    "diagnose-webview-created",
)
replace_once(
    webview_page,
    '''              onLoadStop: (controller, url) {
                setState(() {
                  loadingPercentage = 100;
                  saveCookiesOnWidnows(controller, url);
                });
                widget.onLoadStop?.call(context, controller, url);
              },
              onUpdateVisitedHistory: (controller, url, isReload) {
''',
    '''              onLoadStop: (controller, url) {
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
              onReceivedError: (controller, request, error) {
                unawaited(
                  appendWindowsWebViewDiagnostic(
                    'LOAD_ERROR url=${request.url} type=${error.type} description=${error.description}',
                  ),
                );
              },
              onUpdateVisitedHistory: (controller, url, isReload) {
''',
    "diagnose-webview-navigation",
)
replace_once(
    webview_page,
    '''            ),
          //
          if (loadingPercentage < 100) LinearProgressIndicator(value: loadingPercentage / 100),
''',
    r'''            ),
          if (Platform.isWindows && windowsCreationError != null)
            Positioned.fill(
              child: ColoredBox(
                color: Theme.of(context).colorScheme.surface,
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.error_outline,
                          size: 48,
                          color: Theme.of(context).colorScheme.error,
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'WebView2 no pudo iniciarse',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        SelectableText(
                          windowsCreationError!,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        const SelectableText(
                          r'Diagnóstico: Data\webview-diagnostic.txt',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: () {
                            unawaited(
                              appendWindowsWebViewDiagnostic(
                                'RETRY url=${widget.initialUrl}',
                              ),
                            );
                            setState(() {
                              webViewKey = GlobalKey();
                              controller = Completer<InAppWebViewController>();
                              windowsCreationError = null;
                              loadingPercentage = 0;
                            });
                          },
                          icon: const Icon(Icons.refresh),
                          label: const Text('Reintentar'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          //
          if (loadingPercentage < 100) LinearProgressIndicator(value: loadingPercentage / 100),
''',
    "visible-webview-creation-error-and-retry",
)

# Open the page on the root navigator, normalize scheme-less URLs, and record
# the click before navigation. This separates button/routing problems from
# native WebView creation problems in the portable diagnostic file.
booru_page = Path("lib/src/pages/settings/booru_page.dart")
replace_once(
    booru_page,
    '''        icon: const Icon(Icons.public),
        page: () => InAppWebviewView(initialUrl: selectedBooru!.baseURL!),
''',
    r'''        icon: const Icon(Icons.public),
        action: () async {
          final String rawUrl = selectedBooru?.baseURL?.trim() ?? '';
          if (rawUrl.isEmpty) {
            await appendWindowsWebViewDiagnostic('OPEN_REJECTED empty-url');
            if (!context.mounted) {
              return;
            }
            await showDialog<void>(
              context: context,
              builder: (_) => const AlertDialog(
                title: Text('Open WebView'),
                content: Text('La fuente seleccionada no tiene una URL válida.'),
              ),
            );
            return;
          }

          String targetUrl = rawUrl;
          final Uri? parsed = Uri.tryParse(targetUrl);
          if (parsed == null || parsed.scheme.isEmpty) {
            targetUrl = 'https://$targetUrl';
          }

          await appendWindowsWebViewDiagnostic(
            'OPEN_REQUEST url=$targetUrl booru=${selectedBooru?.name ?? ''}',
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
              'ROUTE_CLOSED url=$targetUrl',
            );
          } catch (e, s) {
            await appendWindowsWebViewDiagnostic(
              'ROUTE_ERROR url=$targetUrl error=$e',
            );
            Logger.Inst().log(
              e.toString(),
              'BooruPage',
              'webviewButton',
              null,
              s: s,
            );
            if (!context.mounted) {
              return;
            }
            await showDialog<void>(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('Error de Open WebView'),
                content: SelectableText(e.toString()),
              ),
            );
          }
        },
''',
    "root-route-and-diagnose-open-webview",
)

# Build-time guards.
pubspec = Path("pubspec.yaml").read_text(encoding="utf-8")
webview_text = webview_page.read_text(encoding="utf-8")
booru_text = booru_page.read_text(encoding="utf-8")
required = {
    "direct Windows dependency": "flutter_inappwebview_windows: ^0.7.0-beta.3" in pubspec,
    "pubspec PR override": PR2838_COMMIT in pubspec,
    "failure stream import": "flutter_inappwebview_windows.dart" in webview_text,
    "creation key": "key: webViewKey" in webview_text,
    "failure listener": "WindowsWebViewCreationFailures.stream.listen" in webview_text,
    "diagnostic path": "webview-diagnostic.txt" in webview_text,
    "visible error": "WebView2 no pudo iniciarse" in webview_text,
    "root navigator": "rootNavigator: true" in booru_text,
    "open request diagnostic": "OPEN_REQUEST" in booru_text,
}
for label, ok in required.items():
    if not ok:
        raise SystemExit(f"V4 guard failed: {label}")

print(f"WINDOWS_WEBVIEW_PLUGIN_PR2838={PR2838_COMMIT}")
print("WINDOWS_WEBVIEW_FAILURE_UI=PASS")
print("WINDOWS_WEBVIEW_PORTABLE_DIAGNOSTIC=PASS")
print("WINDOWS_WEBVIEW_ROOT_ROUTE=PASS")
print("V4_PATCH=PASS")