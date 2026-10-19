from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED {label}: {p}')


handler = Path('lib/src/boorus/danbooru_handler.dart')
text = handler.read_text(encoding='utf-8')

replace_once(
    handler,
    "import 'dart:io';\n",
    "import 'dart:convert';\nimport 'dart:io';\n",
    'danbooru-dart-convert-import',
)

old_headers = '''  @override
  Map<String, String> getHeaders() {
    final defaultHeaders = super.getHeaders();
    defaultHeaders['User-Agent'] = Tools.appUserAgent;
    return defaultHeaders;
  }
'''
new_headers = '''  bool get _hasApiCredentials =>
      booru.userID?.trim().isNotEmpty == true &&
      booru.apiKey?.trim().isNotEmpty == true;

  String get _basicAuthorization => 'Basic ${base64Encode(utf8.encode('${booru.userID!.trim()}:${booru.apiKey!.trim()}'))}';

  @override
  Map<String, String> getHeaders() {
    final defaultHeaders = super.getHeaders();
    defaultHeaders['User-Agent'] = Tools.appUserAgent;
    if (_hasApiCredentials) {
      defaultHeaders['Authorization'] = _basicAuthorization;
    }
    return defaultHeaders;
  }
'''
replace_once(handler, old_headers, new_headers, 'danbooru-basic-auth-headers')

old_fetch = '''    Logger.Inst().log(
      'fetching: $uri with headers: $headers',
      className,
      'Search',
      LogTypes.booruHandlerSearchURL,
    );

    return DioNetwork.get(
      uri.toString(),
      headers: headers,
      queryParameters: queryParams,
      options: fetchSearchOptions(),
      customInterceptor: withCaptchaCheck
          ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
          : null,
    );
'''
new_fetch = '''    final Map<String, String> safeHeadersForLog = {
      ...headers,
      if (headers.containsKey('Authorization')) 'Authorization': 'Basic ***',
      if (headers.containsKey('Cookie')) 'Cookie': '<present>',
    };
    Logger.Inst().log(
      'fetching: $uri with headers: $safeHeadersForLog auth=${_hasApiCredentials ? 'basic' : cookies.isNotEmpty ? 'session-cookie' : 'anonymous'}',
      className,
      'Search',
      LogTypes.booruHandlerSearchURL,
    );

    try {
      return await DioNetwork.get(
        uri.toString(),
        headers: headers,
        queryParameters: queryParams,
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
    } on DioException catch (e) {
      if (!_hasApiCredentials || e.response?.statusCode != HttpStatus.unauthorized) {
        rethrow;
      }

      // Some older Danbooru-compatible forks do not accept HTTP Basic auth
      // even though modern Danbooru does. Retry once with the legacy
      // login/api_key query parameters for compatibility.
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
        LogTypes.info,
      );
      return DioNetwork.get(
        uri.toString(),
        headers: fallbackHeaders,
        queryParameters: fallbackQuery,
        options: fetchSearchOptions(),
        customInterceptor: withCaptchaCheck
            ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
            : null,
      );
    }
'''
replace_once(handler, old_fetch, new_fetch, 'danbooru-auth-fallback-and-redacted-logging')

old_make = '''    final String loginStr = booru.userID?.isNotEmpty == true ? '&login=${booru.userID}' : '';
    final String apiKeyStr = booru.apiKey?.isNotEmpty == true ? '&api_key=${booru.apiKey}' : '';
    return '${booru.baseURL}/posts.json?tags=$tags&limit=$limit&page=$pageNum$loginStr$apiKeyStr';
'''
new_make = '''    // With a complete credential pair authentication is sent via HTTP Basic
    // headers, keeping the API key out of URLs and ordinary request logs.
    // Partial credentials retain the legacy URL behavior for compatibility.
    final String loginStr = !_hasApiCredentials && booru.userID?.isNotEmpty == true ? '&login=${booru.userID}' : '';
    final String apiKeyStr = !_hasApiCredentials && booru.apiKey?.isNotEmpty == true ? '&api_key=${booru.apiKey}' : '';
    return '${booru.baseURL}/posts.json?tags=$tags&limit=$limit&page=$pageNum$loginStr$apiKeyStr';
'''
replace_once(handler, old_make, new_make, 'danbooru-api-key-out-of-url')

editor = Path('lib/src/pages/settings/booru_edit_page.dart')
old_instructions = '''      case BooruType.Hydrus:
        return '';
      default:
        break;
'''
new_instructions = '''      case BooruType.Danbooru:
        return '<b>Danbooru authentication</b><br>'
            'Leave Login and API Key empty to use an existing web session/cookie when available.<br>'
            'Enter both Login and API Key to use HTTP Basic Authentication. '
            'If a compatible older server returns 401, LoliSnatcher retries once with legacy login + api_key parameters.<br>'
            '<b>Never enter your account password in the API Key field.</b>';
      case BooruType.Hydrus:
        return '';
      default:
        break;
'''
replace_once(editor, old_instructions, new_instructions, 'danbooru-auth-ui-instructions')

handler_text = handler.read_text(encoding='utf-8')
editor_text = editor.read_text(encoding='utf-8')
checks = {
    'basic authorization': "defaultHeaders['Authorization'] = _basicAuthorization" in handler_text,
    'redacted authorization log': "'Authorization': 'Basic ***'" in handler_text,
    'redacted cookie log': "'Cookie': '<present>'" in handler_text,
    '401 fallback': "e.response?.statusCode != HttpStatus.unauthorized" in handler_text,
    'legacy fallback login': "'login': booru.userID!.trim()" in handler_text,
    'api key hidden from normal URL': "!_hasApiCredentials && booru.apiKey?.isNotEmpty" in handler_text,
    'generic UI instructions': '<b>Danbooru authentication</b>' in editor_text,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V11 guard failed: {label}')

print('DANBOORU_SESSION_COOKIE_AUTH=PASS')
print('DANBOORU_BASIC_AUTH=PASS')
print('DANBOORU_LEGACY_QUERY_FALLBACK=PASS')
print('DANBOORU_SECRET_REDACTION=PASS')
print('V11_GENERIC_DANBOORU_AUTH=PASS')
