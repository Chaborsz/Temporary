from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


# ---------------------------------------------------------------------------
# Danbooru editor: make credentials explicit instead of exposing the generic
# User ID / API Key rows. We intentionally do NOT store the account password:
# Danbooru third-party API authentication is Login + API Key. The API key acts
# as the API password. Existing saved booru.userID/apiKey values are reused, so
# this is schema-compatible with all previous portable builds.
# ---------------------------------------------------------------------------
editor = 'lib/src/pages/settings/booru_edit_page.dart'

replace_once(
    editor,
    '''  @override
  void dispose() {
    booruNameController.dispose();
    booruURLController.dispose();
    booruFaviconController.dispose();
    booruAPIKeyController.dispose();
    booruUserIDController.dispose();
    booruDefTagsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
''',
    '''  @override
  void dispose() {
    booruNameController.dispose();
    booruURLController.dispose();
    booruFaviconController.dispose();
    booruAPIKeyController.dispose();
    booruUserIDController.dispose();
    booruDefTagsController.dispose();
    super.dispose();
  }

  Future<void> _showDanbooruLoginDialog() async {
    final loginController = TextEditingController(text: booruUserIDController.text);
    final apiKeyController = TextEditingController(text: booruAPIKeyController.text);
    bool obscureApiKey = true;

    final bool apply =
        await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return StatefulBuilder(
              builder: (context, setDialogState) {
                return AlertDialog(
                  title: const Text('Danbooru Login'),
                  content: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 480),
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        spacing: 12,
                        children: [
                          const Text(
                            'La API de Danbooru usa Login + API Key. '
                            'La API Key funciona como contraseña de API; no introduzcas aquí la contraseña real de tu cuenta.',
                          ),
                          TextField(
                            controller: loginController,
                            decoration: const InputDecoration(
                              labelText: 'Login',
                              hintText: 'Nombre de usuario',
                              border: OutlineInputBorder(),
                            ),
                            autocorrect: false,
                            enableSuggestions: false,
                            enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
                          ),
                          TextField(
                            controller: apiKeyController,
                            obscureText: obscureApiKey,
                            decoration: InputDecoration(
                              labelText: 'API Key (contraseña de API)',
                              hintText: 'API Key',
                              border: const OutlineInputBorder(),
                              suffixIcon: IconButton(
                                tooltip: obscureApiKey ? 'Mostrar' : 'Ocultar',
                                onPressed: () {
                                  setDialogState(() {
                                    obscureApiKey = !obscureApiKey;
                                  });
                                },
                                icon: Icon(obscureApiKey ? Icons.visibility : Icons.visibility_off),
                              ),
                            ),
                            autocorrect: false,
                            enableSuggestions: false,
                            enableIMEPersonalizedLearning: false,
                          ),
                          const Text(
                            'Si el servidor no acepta HTTP Basic pero sí el modo legacy login/api_key, '
                            'LoliSnatcher lo detectará una vez y reutilizará ese método durante la sesión.',
                            style: TextStyle(fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () {
                        loginController.clear();
                        apiKeyController.clear();
                        setDialogState(() {});
                      },
                      child: const Text('Limpiar'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.of(dialogContext).pop(false),
                      child: const Text('Cancelar'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.of(dialogContext).pop(true),
                      child: const Text('Aplicar'),
                    ),
                  ],
                );
              },
            );
          },
        ) ??
        false;

    if (apply && mounted) {
      booruUserIDController.text = loginController.text.trim();
      booruAPIKeyController.text = apiKeyController.text.trim();
      _invalidateTestResult();
      setState(() {});
    }

    loginController.dispose();
    apiKeyController.dispose();
  }

  @override
  Widget build(BuildContext context) {
''',
    'danbooru-login-dialog',
)

old_credentials = '''            SettingsTextInput(
              controller: booruUserIDController,
              onChanged: (_) {
                _invalidateTestResult();
                setState(() {});
              },
              title: getUserIDTitle(),
              hintText: getUserIdPlaceholder(),
              clearable: true,
              pasteable: true,
              drawTopBorder: true,
              enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
            ),
            SettingsTextInput(
              controller: booruAPIKeyController,
              onChanged: (_) {
                _invalidateTestResult();
                setState(() {});
              },
              title: getApiKeyTitle(),
              pasteable: true,
              hintText: getApiKeyPlaceholder(),
              clearable: true,
              obscureable: shouldObscureApiKey(),
              enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
            ),
'''
new_credentials = '''            if (selectedBooruType == BooruType.Danbooru)
              SettingsButton(
                name: 'Danbooru Login',
                subtitle: Text(
                  booruUserIDController.text.trim().isNotEmpty && booruAPIKeyController.text.trim().isNotEmpty
                      ? 'Login: ${booruUserIDController.text.trim()} • API Key configurada'
                      : 'Configura Login + API Key',
                ),
                icon: const Icon(Icons.key),
                action: () {
                  unawaited(_showDanbooruLoginDialog());
                },
              )
            else ...[
              SettingsTextInput(
                controller: booruUserIDController,
                onChanged: (_) {
                  _invalidateTestResult();
                  setState(() {});
                },
                title: getUserIDTitle(),
                hintText: getUserIdPlaceholder(),
                clearable: true,
                pasteable: true,
                drawTopBorder: true,
                enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
              ),
              SettingsTextInput(
                controller: booruAPIKeyController,
                onChanged: (_) {
                  _invalidateTestResult();
                  setState(() {});
                },
                title: getApiKeyTitle(),
                pasteable: true,
                hintText: getApiKeyPlaceholder(),
                clearable: true,
                obscureable: shouldObscureApiKey(),
                enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
              ),
            ],
'''
replace_once(editor, old_credentials, new_credentials, 'danbooru-dedicated-login-entry')


# ---------------------------------------------------------------------------
# Danbooru handler: remember a successful legacy login/api_key fallback for the
# lifetime of this handler. Without this, a server that rejects Basic causes an
# avoidable 401 + retry on every search/page request.
# ---------------------------------------------------------------------------
handler = 'lib/src/boorus/danbooru_handler.dart'

replace_once(
    handler,
    '''  bool get _hasApiCredentials =>
      booru.userID?.trim().isNotEmpty == true &&
      booru.apiKey?.trim().isNotEmpty == true;
''',
    '''  bool _preferLegacySearchAuth = false;

  bool get _hasApiCredentials =>
      booru.userID?.trim().isNotEmpty == true &&
      booru.apiKey?.trim().isNotEmpty == true;
''',
    'danbooru-auth-mode-memory',
)

replace_once(
    handler,
    '''    final Map<String, String> safeHeadersForLog = {
      ...headers,
      if (headers.containsKey('Authorization')) 'Authorization': 'Basic ***',
      if (headers.containsKey('Cookie')) 'Cookie': '<present>',
    };
    Logger.Inst().log(
      "fetching: $uri with headers: $safeHeadersForLog auth=${_hasApiCredentials ? 'basic' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}",
      className,
      'Search',
      LogTypes.booruHandlerSearchURL,
    );

    try {
      return await DioNetwork.get(
        uri.toString(),
        headers: headers,
        queryParameters: queryParams,
''',
    '''    final Map<String, String> requestHeaders = Map<String, String>.from(headers);
    Map<String, dynamic>? requestQueryParams = queryParams;
    if (_hasApiCredentials && _preferLegacySearchAuth) {
      requestHeaders.remove('Authorization');
      requestQueryParams = <String, dynamic>{
        ...?queryParams,
        'login': booru.userID!.trim(),
        'api_key': booru.apiKey!.trim(),
      };
    }

    final Map<String, String> safeHeadersForLog = {
      ...requestHeaders,
      if (requestHeaders.containsKey('Authorization')) 'Authorization': 'Basic ***',
      if (requestHeaders.containsKey('Cookie')) 'Cookie': '<present>',
    };
    Logger.Inst().log(
      "fetching: $uri with headers: $safeHeadersForLog auth=${_hasApiCredentials ? _preferLegacySearchAuth ? 'legacy-query' : 'basic' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}",
      className,
      'Search',
      LogTypes.booruHandlerSearchURL,
    );

    try {
      return await DioNetwork.get(
        uri.toString(),
        headers: requestHeaders,
        queryParameters: requestQueryParams,
''',
    'danbooru-sticky-auth-request-selection',
)

replace_once(
    handler,
    '''      if (!_hasApiCredentials || e.response?.statusCode != HttpStatus.unauthorized) {
        rethrow;
      }
''',
    '''      if (!_hasApiCredentials ||
          _preferLegacySearchAuth ||
          e.response?.statusCode != HttpStatus.unauthorized) {
        rethrow;
      }
''',
    'danbooru-no-double-fallback-loop',
)

replace_once(
    handler,
    '''      return DioNetwork.get(
        uri.toString(),
        headers: fallbackHeaders,
        queryParameters: fallbackQuery,
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
''',
    '''      final Response fallbackResponse = await DioNetwork.get(
        uri.toString(),
        headers: fallbackHeaders,
        queryParameters: fallbackQuery,
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
      _preferLegacySearchAuth = true;
      return fallbackResponse;
''',
    'danbooru-remember-successful-legacy-fallback',
)


# Guards.
editor_text = Path(editor).read_text(encoding='utf-8')
handler_text = Path(handler).read_text(encoding='utf-8')
checks = {
    'dialog exists': "title: const Text('Danbooru Login')" in editor_text,
    'login field exists': "labelText: 'Login'" in editor_text,
    'api password field exists': "labelText: 'API Key (contraseña de API)'" in editor_text,
    'account password warning exists': 'no introduzcas aquí la contraseña real de tu cuenta' in editor_text,
    'secret not echoed': 'API Key configurada' in editor_text,
    'sticky legacy state exists': 'bool _preferLegacySearchAuth = false;' in handler_text,
    'legacy mode reused': "'legacy-query'" in handler_text,
    'fallback success remembered': '_preferLegacySearchAuth = true;' in handler_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.3 guard failed: {label}')

print('DANBOORU_LOGIN_DIALOG=PASS')
print('DANBOORU_API_SECRET_HIDDEN=PASS')
print('DANBOORU_STICKY_AUTH_MODE=PASS')
print('V8_3_DANBOORU_LOGIN_UI=PASS')
