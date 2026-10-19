from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


handler = 'lib/src/boorus/danbooru_handler.dart'
editor = 'lib/src/pages/settings/booru_edit_page.dart'

# ---------------------------------------------------------------------------
# Correct Danbooru semantics.
#
# Danbooru API authentication is a PAIR: login + api_key. A lone API key is
# not an authenticated account. Public endpoints can still return HTTP 200,
# which previously created the false impression that API-key-only auth worked.
# Use the official login/api_key query form for the complete pair; never send
# partial API credentials and never infer login success from a public search.
# ---------------------------------------------------------------------------
replace_once(
    handler,
    "import 'dart:convert';\nimport 'dart:io';\n",
    "import 'dart:io';\n",
    'remove-basic-auth-import',
)

replace_once(
    handler,
    '''  bool _preferLegacySearchAuth = false;

  bool get _hasApiCredentials =>
      booru.userID?.trim().isNotEmpty == true &&
      booru.apiKey?.trim().isNotEmpty == true;

  String get _basicAuthorization =>
      'Basic ${base64Encode(utf8.encode("${booru.userID!.trim()}:${booru.apiKey!.trim()}"))}';

  @override
  Map<String, String> getHeaders() {
    final defaultHeaders = super.getHeaders();
    defaultHeaders['User-Agent'] = Tools.appUserAgent;
    if (_hasApiCredentials) {
      defaultHeaders['Authorization'] = _basicAuthorization;
    }
    return defaultHeaders;
  }
''',
    '''  bool get _hasApiKey => booru.apiKey?.trim().isNotEmpty == true;
  bool get _hasLogin => booru.userID?.trim().isNotEmpty == true;
  bool get _hasCompleteApiCredentials => _hasApiKey && _hasLogin;

  @override
  Map<String, String> getHeaders() {
    final defaultHeaders = super.getHeaders();
    defaultHeaders['User-Agent'] = Tools.appUserAgent;
    return defaultHeaders;
  }
''',
    'danbooru-complete-pair-auth-state',
)

old_fetch = '''    final Map<String, String> requestHeaders = Map<String, String>.from(headers);
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
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
    } on DioException catch (e) {
      if (!_hasApiCredentials ||
          _preferLegacySearchAuth ||
          e.response?.statusCode != HttpStatus.unauthorized) {
        rethrow;
      }

      // Some older Danbooru-compatible forks do not accept HTTP Basic auth.
      // Retry exactly once using the legacy login/api_key query parameters.
      final Map<String, String> fallbackHeaders = Map<String, String>.from(headers)..remove('Authorization');
      final Map<String, dynamic> fallbackQuery = <String, dynamic>{
        ...?queryParams,
        'login': booru.userID!.trim(),
        'api_key': booru.apiKey!.trim(),
      };
      Logger.Inst().log(
        'Danbooru Basic auth returned 401; retrying once with legacy login/api_key parameters',
        className,
        'Search',
        LogTypes.booruHandlerInfo,
      );
      final Response fallbackResponse = await DioNetwork.get(
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
    }
'''
new_fetch = '''    final Map<String, String> requestHeaders = Map<String, String>.from(headers)
      ..remove('Authorization');
    Map<String, dynamic>? requestQueryParams = queryParams;
    if (_hasCompleteApiCredentials) {
      requestQueryParams = <String, dynamic>{
        ...?queryParams,
        'login': booru.userID!.trim(),
        'api_key': booru.apiKey!.trim(),
      };
    }

    final Map<String, String> safeHeadersForLog = {
      ...requestHeaders,
      if (requestHeaders.containsKey('Cookie')) 'Cookie': '<present>',
    };
    Logger.Inst().log(
      "fetching: $uri with headers: $safeHeadersForLog auth=${_hasCompleteApiCredentials ? 'login+api-key-query' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}",
      className,
      'Search',
      LogTypes.booruHandlerSearchURL,
    );

    return DioNetwork.get(
      uri.toString(),
      headers: requestHeaders,
      queryParameters: requestQueryParams,
      options: fetchSearchOptions(),
      customInterceptor: withCaptchaCheck
          ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
          : null,
    );
'''
replace_once(handler, old_fetch, new_fetch, 'danbooru-complete-pair-search-auth')

replace_once(
    handler,
    '''      final res = await DioNetwork.get(
        '${booru.baseURL}/users.json',
        headers: getHeaders(),
        queryParameters: {
          'search[id]': item.uploaderId,
        },
      );
''',
    '''      final res = await DioNetwork.get(
        '${booru.baseURL}/users.json',
        headers: getHeaders(),
        queryParameters: {
          'search[id]': item.uploaderId,
          if (_hasCompleteApiCredentials) 'login': booru.userID!.trim(),
          if (_hasCompleteApiCredentials) 'api_key': booru.apiKey!.trim(),
        },
      );
''',
    'danbooru-complete-pair-aux-auth',
)

# ---------------------------------------------------------------------------
# Editor: validate the credentials against /profile.json. Danbooru's profile
# JSON returns CurrentUser.user, so this proves which account the API actually
# authenticated instead of merely testing a public endpoint.
# ---------------------------------------------------------------------------
replace_once(
    editor,
    "import 'package:flutter/material.dart';\n\n",
    "import 'package:flutter/material.dart';\n\nimport 'package:dio/dio.dart';\n",
    'danbooru-login-dio-import',
)
replace_once(
    editor,
    "import 'package:lolisnatcher/src/utils/content_policy.dart';\n",
    "import 'package:lolisnatcher/src/utils/content_policy.dart';\nimport 'package:lolisnatcher/src/utils/dio_network.dart';\n",
    'danbooru-login-dionetwork-import',
)

replace_once(
    editor,
    '''  BooruType? booruType;
  BooruType selectedBooruType = BooruType.Autodetect;
  String? _lastSuccessfulTestSignature;
''',
    '''  BooruType? booruType;
  BooruType selectedBooruType = BooruType.Autodetect;
  String? _lastSuccessfulTestSignature;
  String? _verifiedDanbooruLogin;
''',
    'danbooru-verified-login-state',
)

p = Path(editor)
text = p.read_text(encoding='utf-8')
start_marker = '  Future<void> _showDanbooruLoginDialog() async {'
end_marker = '\n  @override\n  Widget build(BuildContext context) {'
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('danbooru-verified-login-dialog: markers not found')

new_dialog = '''  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(
    String login,
    String apiKey,
  ) async {
    final normalizedLogin = login.trim();
    final normalizedApiKey = apiKey.trim();
    if (normalizedLogin.isEmpty || normalizedApiKey.isEmpty) {
      return (ok: false, message: 'Debes completar Login y API Key.', userName: null);
    }

    String baseUrl = booruURLController.text.trim();
    if (!baseUrl.contains('://')) {
      baseUrl = 'https://$baseUrl';
    }
    while (baseUrl.endsWith('/')) {
      baseUrl = baseUrl.substring(0, baseUrl.length - 1);
    }
    if (baseUrl.isEmpty) {
      return (ok: false, message: 'Primero configura la URL del booru.', userName: null);
    }

    try {
      final response = await DioNetwork.get(
        '$baseUrl/profile.json',
        headers: {'User-Agent': Tools.appUserAgent},
        queryParameters: {
          'login': normalizedLogin,
          'api_key': normalizedApiKey,
        },
      );
      final data = response.data;
      if (data is! Map) {
        return (ok: false, message: 'El servidor no devolvió un perfil de usuario válido.', userName: null);
      }
      final userName = data['name']?.toString().trim();
      final userId = data['id']?.toString().trim();
      final expected = normalizedLogin.toLowerCase().replaceAll(' ', '_');
      final actual = (userName ?? '').toLowerCase().replaceAll(' ', '_');
      if (userName == null || userName.isEmpty || actual != expected) {
        return (
          ok: false,
          message: userName?.isNotEmpty == true
              ? 'El servidor respondió como "$userName", no como "$normalizedLogin".'
              : 'El servidor no confirmó la identidad de la cuenta.',
          userName: userName,
        );
      }
      return (
        ok: true,
        message: 'Autenticado como $userName${userId?.isNotEmpty == true ? ' (ID $userId)' : ''}.',
        userName: userName,
      );
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      if (status == 401) {
        return (
          ok: false,
          message: '401: Login o API Key incorrectos, o la API Key no pertenece a ese usuario.',
          userName: null,
        );
      }
      if (status == 403) {
        return (
          ok: false,
          message: '403: la API Key fue reconocida pero no tiene permiso para validar este acceso.',
          userName: null,
        );
      }
      return (
        ok: false,
        message: status != null ? 'Error HTTP $status al validar el login.' : 'No se pudo validar el login: ${e.type.name}.',
        userName: null,
      );
    } catch (e) {
      return (ok: false, message: 'No se pudo validar el login: $e', userName: null);
    }
  }

  Future<void> _showDanbooruLoginDialog() async {
    final loginController = TextEditingController(text: booruUserIDController.text);
    final apiKeyController = TextEditingController(text: booruAPIKeyController.text);
    bool obscureApiKey = true;
    bool isChecking = false;
    String? statusMessage;
    bool? statusOk;
    String? verifiedLogin;

    final bool apply =
        await showDialog<bool>(
          context: context,
          builder: (dialogContext) {
            return StatefulBuilder(
              builder: (context, setDialogState) {
                Future<void> validateAndApply() async {
                  final login = loginController.text.trim();
                  final apiKey = apiKeyController.text.trim();
                  if (login.isEmpty && apiKey.isEmpty) {
                    verifiedLogin = null;
                    if (dialogContext.mounted) {
                      Navigator.of(dialogContext).pop(true);
                    }
                    return;
                  }
                  if (login.isEmpty || apiKey.isEmpty) {
                    setDialogState(() {
                      statusOk = false;
                      statusMessage = 'Debes completar Login y API Key; uno solo no autentica la cuenta.';
                    });
                    return;
                  }
                  setDialogState(() {
                    isChecking = true;
                    statusOk = null;
                    statusMessage = 'Validando /profile.json…';
                  });
                  final result = await _verifyDanbooruLogin(login, apiKey);
                  if (!dialogContext.mounted) return;
                  setDialogState(() {
                    isChecking = false;
                    statusOk = result.ok;
                    statusMessage = result.message;
                  });
                  if (result.ok) {
                    verifiedLogin = result.userName;
                    Navigator.of(dialogContext).pop(true);
                  }
                }

                return AlertDialog(
                  title: const Text('Danbooru Login'),
                  content: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 500),
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        spacing: 12,
                        children: [
                          const Text(
                            'Danbooru autentica la API con el par Login + API Key. '
                            'Una búsqueda pública que responde 200 no demuestra que hayas iniciado sesión.',
                          ),
                          TextField(
                            controller: loginController,
                            decoration: const InputDecoration(
                              labelText: 'Login',
                              hintText: 'Nombre de usuario de Danbooru',
                              border: OutlineInputBorder(),
                            ),
                            autocorrect: false,
                            enableSuggestions: false,
                            enableIMEPersonalizedLearning: !settingsHandler.incognitoKeyboard,
                            onChanged: (_) {
                              setDialogState(() {
                                statusOk = null;
                                statusMessage = null;
                              });
                            },
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
                            onChanged: (_) {
                              setDialogState(() {
                                statusOk = null;
                                statusMessage = null;
                              });
                            },
                          ),
                          const Text(
                            '“Validar y aplicar” consulta /profile.json con esas credenciales. '
                            'Solo se aceptan si el servidor devuelve tu usuario real. No uses la contraseña normal de tu cuenta.',
                            style: TextStyle(fontSize: 12),
                          ),
                          if (statusMessage != null)
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (isChecking)
                                  const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                else
                                  Icon(
                                    statusOk == true ? Icons.verified_user : Icons.error_outline,
                                    size: 20,
                                    color: statusOk == true ? Colors.green : Colors.red,
                                  ),
                                const SizedBox(width: 8),
                                Expanded(child: Text(statusMessage!)),
                              ],
                            ),
                        ],
                      ),
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: isChecking
                          ? null
                          : () {
                              loginController.clear();
                              apiKeyController.clear();
                              setDialogState(() {
                                statusOk = null;
                                statusMessage = null;
                              });
                            },
                      child: const Text('Limpiar'),
                    ),
                    TextButton(
                      onPressed: isChecking ? null : () => Navigator.of(dialogContext).pop(false),
                      child: const Text('Cancelar'),
                    ),
                    FilledButton.icon(
                      onPressed: isChecking ? null : validateAndApply,
                      icon: const Icon(Icons.verified_user),
                      label: const Text('Validar y aplicar'),
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
      _verifiedDanbooruLogin = verifiedLogin;
      setState(() {});
    }

    loginController.dispose();
    apiKeyController.dispose();
  }
'''
p.write_text(text[:start] + new_dialog + text[end:], encoding='utf-8')
print('PATCHED danbooru-verified-login-dialog:', p)

replace_once(
    editor,
    '''                  booruUserIDController.text.trim().isNotEmpty && booruAPIKeyController.text.trim().isNotEmpty
                      ? 'Login: ${booruUserIDController.text.trim()} • API Key configurada'
                      : 'Configura Login + API Key',
''',
    '''                  _verifiedDanbooruLogin != null
                      ? 'Autenticado como $_verifiedDanbooruLogin'
                      : booruUserIDController.text.trim().isNotEmpty && booruAPIKeyController.text.trim().isNotEmpty
                      ? 'Credenciales configuradas • sin verificar'
                      : 'Configura Login + API Key',
''',
    'danbooru-auth-status-summary',
)

replace_once(
    editor,
    '''        return '<b>Danbooru authentication</b><br>'
            'Leave Login and API Key empty to use an existing web session/cookie when available.<br>'
            'Enter both Login and API Key to use HTTP Basic Authentication. '
            'If a compatible older server returns 401, LoliSnatcher retries once with legacy login + api_key parameters.<br>'
            '<b>Never enter your account password in the API Key field.</b>';
''',
    '''        return '<b>Danbooru authentication</b><br>'
            'Authenticated API access requires both Login and API Key. A lone API Key is not treated as a login.<br>'
            'Use Danbooru Login to validate /profile.json; only a response identifying your account is considered authenticated.<br>'
            '<b>Never enter your account password in the API Key field.</b>';
''',
    'danbooru-verified-auth-instructions',
)

insert_after = '''    if (!ContentPolicy.isBooruTypeAllowed(selectedBooruType)) {
      showSourceUnavailableMessage();
      return false;
    }

    booruFaviconController.text = booruFaviconController.text.trim().isEmpty
'''
replacement = '''    if (!ContentPolicy.isBooruTypeAllowed(selectedBooruType)) {
      showSourceUnavailableMessage();
      return false;
    }

    if (selectedBooruType == BooruType.Danbooru) {
      final hasLogin = booruUserIDController.text.trim().isNotEmpty;
      final hasApiKey = booruAPIKeyController.text.trim().isNotEmpty;
      if (hasLogin != hasApiKey) {
        FlashElements.showSnackbar(
          context: context,
          title: const Text('Danbooru Login incompleto', style: TextStyle(fontSize: 20)),
          content: const Text('Para autenticar la cuenta debes configurar Login y API Key juntos.'),
          leadingIcon: Icons.warning_amber,
          leadingIconColor: Colors.red,
          sideColor: Colors.red,
        );
        return false;
      }
      if (hasLogin && hasApiKey) {
        final authResult = await _verifyDanbooruLogin(
          booruUserIDController.text,
          booruAPIKeyController.text,
        );
        if (!authResult.ok) {
          _verifiedDanbooruLogin = null;
          FlashElements.showSnackbar(
            context: context,
            duration: const Duration(seconds: 6),
            title: const Text('Danbooru Login falló', style: TextStyle(fontSize: 20)),
            content: Text(authResult.message),
            leadingIcon: Icons.error_outline,
            leadingIconColor: Colors.red,
            sideColor: Colors.red,
          );
          return false;
        }
        _verifiedDanbooruLogin = authResult.userName;
        setState(() {});
      } else {
        _verifiedDanbooruLogin = null;
      }
    }

    booruFaviconController.text = booruFaviconController.text.trim().isEmpty
'''
replace_once(editor, insert_after, replacement, 'danbooru-save-requires-profile-verification')

handler_text = Path(handler).read_text(encoding='utf-8')
editor_text = Path(editor).read_text(encoding='utf-8')
checks = {
    'complete credentials only': 'bool get _hasCompleteApiCredentials => _hasApiKey && _hasLogin;' in handler_text,
    'basic auth removed': "defaultHeaders['Authorization']" not in handler_text,
    'legacy heuristic removed': '_preferLegacySearchAuth' not in handler_text,
    'paired query auth': "'login': booru.userID!.trim(),\n        'api_key': booru.apiKey!.trim()" in handler_text,
    'profile verification endpoint': "'$baseUrl/profile.json'" in editor_text,
    'profile identity checked': "data['name']" in editor_text,
    '401 explicit': '401: Login o API Key incorrectos' in editor_text,
    'verified summary': 'Autenticado como $_verifiedDanbooruLogin' in editor_text,
    'partial credentials rejected': 'Danbooru Login incompleto' in editor_text,
    'public success not auth': 'Una búsqueda pública que responde 200 no demuestra' in editor_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.5 guard failed: {label}')

print('DANBOORU_COMPLETE_PAIR_AUTH=PASS')
print('DANBOORU_PROFILE_IDENTITY_VERIFY=PASS')
print('DANBOORU_PARTIAL_CREDS_REJECTED=PASS')
print('DANBOORU_PUBLIC_200_NOT_LOGIN=PASS')
print('V8_5_VERIFIED_DANBOORU_LOGIN=PASS')
