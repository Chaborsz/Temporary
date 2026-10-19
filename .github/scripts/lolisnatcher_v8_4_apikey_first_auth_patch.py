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

# Do not let merely filling the username switch Danbooru requests to HTTP Basic.
# The server reported by the tester accepts API-key-only requests but returns 401
# once a username makes the old patch choose Basic auth. Start with the known-good
# API-key-only query mode. Only add login after a 401, and remember that successful
# fallback for the rest of this handler session.
replace_once(
    handler,
    "import 'dart:convert';\nimport 'dart:io';\n",
    "import 'dart:io';\n",
    'remove-unused-basic-auth-import',
)

replace_once(
    handler,
    '''  bool _preferLegacySearchAuth = false;\n\n  bool get _hasApiCredentials =>\n      booru.userID?.trim().isNotEmpty == true &&\n      booru.apiKey?.trim().isNotEmpty == true;\n\n  String get _basicAuthorization =>\n      'Basic ${base64Encode(utf8.encode("${booru.userID!.trim()}:${booru.apiKey!.trim()}"))}';\n\n  @override\n  Map<String, String> getHeaders() {\n    final defaultHeaders = super.getHeaders();\n    defaultHeaders['User-Agent'] = Tools.appUserAgent;\n    if (_hasApiCredentials) {\n      defaultHeaders['Authorization'] = _basicAuthorization;\n    }\n    return defaultHeaders;\n  }\n''',
    '''  bool _preferLoginQueryAuth = false;\n\n  bool get _hasApiKey => booru.apiKey?.trim().isNotEmpty == true;\n  bool get _hasLogin => booru.userID?.trim().isNotEmpty == true;\n\n  @override\n  Map<String, String> getHeaders() {\n    final defaultHeaders = super.getHeaders();\n    defaultHeaders['User-Agent'] = Tools.appUserAgent;\n    return defaultHeaders;\n  }\n''',
    'danbooru-apikey-first-auth-state',
)

replace_once(
    handler,
    '''    final Map<String, String> requestHeaders = Map<String, String>.from(headers);\n    Map<String, dynamic>? requestQueryParams = queryParams;\n    if (_hasApiCredentials && _preferLegacySearchAuth) {\n      requestHeaders.remove('Authorization');\n      requestQueryParams = <String, dynamic>{\n        ...?queryParams,\n        'login': booru.userID!.trim(),\n        'api_key': booru.apiKey!.trim(),\n      };\n    }\n\n    final Map<String, String> safeHeadersForLog = {\n      ...requestHeaders,\n      if (requestHeaders.containsKey('Authorization')) 'Authorization': 'Basic ***',\n      if (requestHeaders.containsKey('Cookie')) 'Cookie': '<present>',\n    };\n    Logger.Inst().log(\n      "fetching: $uri with headers: $safeHeadersForLog auth=${_hasApiCredentials ? _preferLegacySearchAuth ? 'legacy-query' : 'basic' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}",\n      className,\n      'Search',\n      LogTypes.booruHandlerSearchURL,\n    );\n\n    try {\n      return await DioNetwork.get(\n        uri.toString(),\n        headers: requestHeaders,\n        queryParameters: requestQueryParams,\n        options: fetchSearchOptions(),\n        customInterceptor: withCaptchaCheck\n            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)\n            : null,\n      );\n    } on DioException catch (e) {\n      if (!_hasApiCredentials ||\n          _preferLegacySearchAuth ||\n          e.response?.statusCode != HttpStatus.unauthorized) {\n        rethrow;\n      }\n\n      // Some older Danbooru-compatible forks do not accept HTTP Basic auth.\n      // Retry exactly once using the legacy login/api_key query parameters.\n      final Map<String, String> fallbackHeaders = Map<String, String>.from(headers)..remove('Authorization');\n      final Map<String, dynamic> fallbackQuery = <String, dynamic>{\n        ...?queryParams,\n        'login': booru.userID!.trim(),\n        'api_key': booru.apiKey!.trim(),\n      };\n      Logger.Inst().log(\n        'Danbooru Basic auth returned 401; retrying once with legacy login/api_key parameters',\n        className,\n        'Search',\n        LogTypes.booruHandlerInfo,\n      );\n      final Response fallbackResponse = await DioNetwork.get(\n        uri.toString(),\n        headers: fallbackHeaders,\n        queryParameters: fallbackQuery,\n        options: fetchSearchOptions(),\n        customInterceptor: withCaptchaCheck\n            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)\n            : null,\n      );\n      _preferLegacySearchAuth = true;\n      return fallbackResponse;\n    }\n''',
    '''    final Map<String, String> requestHeaders = Map<String, String>.from(headers)\n      ..remove('Authorization');\n    Map<String, dynamic>? requestQueryParams = queryParams;\n    if (_hasApiKey) {\n      requestQueryParams = <String, dynamic>{\n        ...?queryParams,\n        if (_preferLoginQueryAuth && _hasLogin) 'login': booru.userID!.trim(),\n        'api_key': booru.apiKey!.trim(),\n      };\n    }\n\n    final Map<String, String> safeHeadersForLog = {\n      ...requestHeaders,\n      if (requestHeaders.containsKey('Cookie')) 'Cookie': '<present>',\n    };\n    Logger.Inst().log(\n      "fetching: $uri with headers: $safeHeadersForLog auth=${_hasApiKey ? _preferLoginQueryAuth && _hasLogin ? 'login+api-key-query' : 'api-key-only-query' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}",\n      className,\n      'Search',\n      LogTypes.booruHandlerSearchURL,\n    );\n\n    try {\n      return await DioNetwork.get(\n        uri.toString(),\n        headers: requestHeaders,\n        queryParameters: requestQueryParams,\n        options: fetchSearchOptions(),\n        customInterceptor: withCaptchaCheck\n            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)\n            : null,\n      );\n    } on DioException catch (e) {\n      if (!_hasApiKey ||\n          !_hasLogin ||\n          _preferLoginQueryAuth ||\n          e.response?.statusCode != HttpStatus.unauthorized) {\n        rethrow;\n      }\n\n      // API-key-only is the preferred mode because some Danbooru-compatible\n      // servers reject requests as soon as a login is supplied. Add login only\n      // after an actual 401 and remember it if that fallback succeeds.\n      final Map<String, dynamic> fallbackQuery = <String, dynamic>{\n        ...?queryParams,\n        'login': booru.userID!.trim(),\n        'api_key': booru.apiKey!.trim(),\n      };\n      Logger.Inst().log(\n        'Danbooru API-key-only auth returned 401; retrying once with login + api_key',\n        className,\n        'Search',\n        LogTypes.booruHandlerInfo,\n      );\n      final Response fallbackResponse = await DioNetwork.get(\n        uri.toString(),\n        headers: requestHeaders,\n        queryParameters: fallbackQuery,\n        options: fetchSearchOptions(),\n        customInterceptor: withCaptchaCheck\n            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)\n            : null,\n      );\n      _preferLoginQueryAuth = true;\n      return fallbackResponse;\n    }\n''',
    'danbooru-apikey-first-search-flow',
)

# Auxiliary Danbooru GETs should follow the same chosen query-auth mode instead
# of silently reintroducing Basic auth.
replace_once(
    handler,
    '''      final res = await DioNetwork.get(\n        '${booru.baseURL}/users.json',\n        headers: getHeaders(),\n        queryParameters: {\n          'search[id]': item.uploaderId,\n        },\n      );\n''',
    '''      final res = await DioNetwork.get(\n        '${booru.baseURL}/users.json',\n        headers: getHeaders(),\n        queryParameters: {\n          'search[id]': item.uploaderId,\n          if (_hasApiKey) 'api_key': booru.apiKey!.trim(),\n          if (_hasApiKey && _hasLogin && _preferLoginQueryAuth) 'login': booru.userID!.trim(),\n        },\n      );\n''',
    'danbooru-aux-apikey-query-auth',
)

# Update the editor copy so the UI describes what the handler actually does.
replace_once(
    editor,
    '''        return '<b>Danbooru authentication</b><br>'\n            'Leave Login and API Key empty to use an existing web session/cookie when available.<br>'\n            'Enter both Login and API Key to use HTTP Basic Authentication. '\n            'If a compatible older server returns 401, LoliSnatcher retries once with legacy login + api_key parameters.<br>'\n            '<b>Never enter your account password in the API Key field.</b>';\n''',
    '''        return '<b>Danbooru authentication</b><br>'\n            'API Key is used first and can work by itself. Login is optional.<br>'\n            'If API Key alone returns 401 and Login is configured, LoliSnatcher retries once with login + api_key and remembers that mode for the session.<br>'\n            '<b>Never enter your account password in the API Key field.</b>';\n''',
    'danbooru-apikey-first-instructions',
)

replace_once(
    editor,
    '''                          const Text(\n                            'La API de Danbooru usa Login + API Key. '\n                            'La API Key funciona como contraseña de API; no introduzcas aquí la contraseña real de tu cuenta.',\n                          ),\n''',
    '''                          const Text(\n                            'La API Key se usa primero y puede funcionar sola. El Login es opcional. '\n                            'Si la API Key sola devuelve 401, LoliSnatcher probará una vez Login + API Key. '\n                            'No introduzcas aquí la contraseña real de tu cuenta.',\n                          ),\n''',
    'danbooru-dialog-apikey-first-copy',
)

replace_once(
    editor,
    '''                          const Text(\n                            'Si el servidor no acepta HTTP Basic pero sí el modo legacy login/api_key, '\n                            'LoliSnatcher lo detectará una vez y reutilizará ese método durante la sesión.',\n                            style: TextStyle(fontSize: 12),\n                          ),\n''',
    '''                          const Text(\n                            'Guardar un Login ya no cambia automáticamente el método de autenticación. '\n                            'Mientras API Key sola funcione, ese será el modo utilizado.',\n                            style: TextStyle(fontSize: 12),\n                          ),\n''',
    'danbooru-dialog-no-basic-copy',
)

handler_text = Path(handler).read_text(encoding='utf-8')
editor_text = Path(editor).read_text(encoding='utf-8')
checks = {
    'api key getter': 'bool get _hasApiKey' in handler_text,
    'login optional getter': 'bool get _hasLogin' in handler_text,
    'no basic authorization': "defaultHeaders['Authorization']" not in handler_text,
    'api key first query': "'api_key': booru.apiKey!.trim()" in handler_text,
    'login conditional': "if (_preferLoginQueryAuth && _hasLogin) 'login'" in handler_text,
    'fallback remembered': '_preferLoginQueryAuth = true;' in handler_text,
    'ui says login optional': 'El Login es opcional' in editor_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.4 guard failed: {label}')

print('DANBOORU_APIKEY_FIRST=PASS')
print('DANBOORU_USERNAME_OPTIONAL=PASS')
print('DANBOORU_NO_AUTO_BASIC_AUTH=PASS')
print('DANBOORU_LOGIN_FALLBACK_ONLY_AFTER_401=PASS')
print('V8_4_APIKEY_FIRST_AUTH=PASS')
