from pathlib import Path

editor = Path('lib/src/pages/settings/booru_edit_page.dart')
text = editor.read_text(encoding='utf-8')

# v8.7 fixes the runtime case where validation reached an HTML page instead of
# the Danbooru JSON API. Normalize the configured URL to the API origin, use
# official Basic Auth first (with login+api_key query fallback for compatible
# forks), and run the same captcha/anti-bot interceptor used by normal searches.
start_marker = "  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(\n"
end_marker = "\n  Future<void> _showDanbooruLoginDialog() async {"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('v8.7: could not locate v8.6 Danbooru validator')

new_validator = r'''  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(
    String login,
    String apiKey,
  ) async {
    final normalizedLogin = login.trim();
    final normalizedApiKey = apiKey.trim();
    if (normalizedLogin.isEmpty || normalizedApiKey.isEmpty) {
      return (ok: false, message: 'Debes completar Login y API Key.', userName: null);
    }

    String configuredUrl = booruURLController.text.trim();
    if (!configuredUrl.contains('://')) {
      configuredUrl = 'https://$configuredUrl';
    }
    final configuredUri = Uri.tryParse(configuredUrl);
    if (configuredUri == null || !configuredUri.hasScheme || configuredUri.host.isEmpty) {
      return (ok: false, message: 'La URL del booru no es válida.', userName: null);
    }

    // Danbooru API routes (/profile.json, /users.json, /posts.json) live at
    // the site root. A pasted browser URL such as /posts must not become
    // /posts/profile.json.
    final apiRootUri = configuredUri.replace(path: '', query: null, fragment: null);
    final apiRoot = apiRootUri.toString().replaceFirst(RegExp(r'/$'), '');
    final expected = normalizedLogin.toLowerCase().replaceAll(' ', '_');
    final basicAuthorization = 'Basic ${base64Encode(utf8.encode('$normalizedLogin:$normalizedApiKey'))}';

    dynamic decodeBody(dynamic value) {
      if (value is! String) return value;
      final body = value.trim();
      if (body.isEmpty) return null;
      try {
        return jsonDecode(body);
      } catch (_) {
        return value;
      }
    }

    Map<dynamic, dynamic>? findExactUser(dynamic raw) {
      final decoded = decodeBody(raw);
      final List<dynamic> candidates = [];
      if (decoded is List) {
        candidates.addAll(decoded);
      } else if (decoded is Map) {
        if (decoded['users'] is List) candidates.addAll(decoded['users'] as List);
        if (decoded['user'] is Map) candidates.add(decoded['user']);
        if (decoded['data'] is Map) candidates.add(decoded['data']);
        if (decoded.containsKey('name')) candidates.add(decoded);
      }
      for (final candidate in candidates) {
        if (candidate is! Map) continue;
        final name = candidate['name']?.toString().trim();
        final actual = (name ?? '').toLowerCase().replaceAll(' ', '_');
        if (name != null && name.isNotEmpty && actual == expected) return candidate;
      }
      return null;
    }

    String safeUri(Uri uri) => '${uri.scheme}://${uri.authority}${uri.path}';

    String responseDescription(Response<dynamic>? response) {
      if (response == null) return 'sin respuesta';
      final contentType = response.headers.value(Headers.contentTypeHeader) ?? 'sin content-type';
      return 'HTTP ${response.statusCode}, ${response.data.runtimeType}, $contentType, final=${safeUri(response.realUri)}';
    }

    Dio withCaptcha(Dio dio) =>
        DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent);

    Future<Response<dynamic>> requestApi(
      String path, {
      Map<String, dynamic>? query,
    }) async {
      final headers = <String, dynamic>{
        'User-Agent': Tools.appUserAgent,
        'Accept': 'application/json',
        'Authorization': basicAuthorization,
      };
      try {
        return await DioNetwork.get(
          '$apiRoot$path',
          headers: headers,
          queryParameters: query,
          customInterceptor: withCaptcha,
        );
      } on DioException catch (e) {
        if (e.response?.statusCode != 401) rethrow;

        // Compatibility fallback: Danbooru supports both Basic Auth and the
        // login+api_key query pair. Keep this retry single and credential-safe.
        return DioNetwork.get(
          '$apiRoot$path',
          headers: {
            'User-Agent': Tools.appUserAgent,
            'Accept': 'application/json',
          },
          queryParameters: <String, dynamic>{
            ...?query,
            'login': normalizedLogin,
            'api_key': normalizedApiKey,
          },
          customInterceptor: withCaptcha,
        );
      }
    }

    Response<dynamic>? profileResponse;
    DioException? profileError;
    try {
      // Profile is the strongest identity proof because it represents the
      // authenticated CurrentUser, not merely a public user search.
      profileResponse = await requestApi('/profile.json');
      final user = findExactUser(profileResponse.data);
      if (user != null) {
        final userName = user['name']!.toString().trim();
        final userId = user['id']?.toString().trim();
        return (
          ok: true,
          message: 'Autenticado como $userName${userId?.isNotEmpty == true ? ' (ID $userId)' : ''}.',
          userName: userName,
        );
      }
    } on DioException catch (e) {
      profileError = e;
      if (e.response?.statusCode == 401) {
        return (
          ok: false,
          message: '401: Login o API Key incorrectos, o la API Key no pertenece a ese usuario.',
          userName: null,
        );
      }
    }

    Response<dynamic>? usersResponse;
    DioException? usersError;
    try {
      usersResponse = await requestApi(
        '/users.json',
        query: {
          'search[name_matches]': normalizedLogin,
          'limit': 5,
        },
      );
      final user = findExactUser(usersResponse.data);
      if (user != null) {
        // Only accept the users fallback when the response itself was JSON.
        // This avoids treating an HTML page containing the username as auth.
        final contentType = usersResponse.headers.value(Headers.contentTypeHeader)?.toLowerCase() ?? '';
        final decoded = decodeBody(usersResponse.data);
        if (contentType.contains('json') || decoded is Map || decoded is List) {
          final userName = user['name']!.toString().trim();
          final userId = user['id']?.toString().trim();
          return (
            ok: true,
            message: 'Autenticado como $userName${userId?.isNotEmpty == true ? ' (ID $userId)' : ''}.',
            userName: userName,
          );
        }
      }
    } on DioException catch (e) {
      usersError = e;
      if (e.response?.statusCode == 401) {
        return (
          ok: false,
          message: '401: Login o API Key incorrectos, o la API Key no pertenece a ese usuario.',
          userName: null,
        );
      }
    }

    final profileStatus = profileError?.response?.statusCode;
    final usersStatus = usersError?.response?.statusCode;
    if (profileStatus == 403 || usersStatus == 403) {
      return (
        ok: false,
        message: '403: las credenciales fueron reconocidas, pero la API Key no permite el endpoint de validación.',
        userName: null,
      );
    }

    final profileInfo = profileError != null
        ? 'profile: HTTP ${profileError.response?.statusCode ?? '?'}'
        : 'profile: ${responseDescription(profileResponse)}';
    final usersInfo = usersError != null
        ? 'users: HTTP ${usersError.response?.statusCode ?? '?'}'
        : 'users: ${responseDescription(usersResponse)}';
    final configuredPath = configuredUri.path.isEmpty || configuredUri.path == '/'
        ? ''
        : ' URL normalizada desde ${safeUri(configuredUri)} a $apiRoot.';
    final htmlSeen = [profileResponse, usersResponse].any((response) {
      final type = response?.headers.value(Headers.contentTypeHeader)?.toLowerCase() ?? '';
      return type.contains('text/html');
    });
    final htmlHint = htmlSeen
        ? ' La API sigue devolviendo HTML después del chequeo anti-bot; revisa la ruta final indicada (posible challenge o redirección).'
        : '';
    return (
      ok: false,
      message: 'No se pudo confirmar la identidad. $profileInfo; $usersInfo.$configuredPath$htmlHint',
      userName: null,
    );
  }
'''

text = text[:start] + new_validator + text[end:]
text = text.replace(
    "'“Validar y aplicar” comprueba Login + API Key contra la API de usuarios y usa /profile.json solo como fallback. '",
    "'“Validar y aplicar” usa el API root, Basic Auth y el mismo chequeo anti-bot que las búsquedas; login + api_key queda como fallback. '",
)
editor.write_text(text, encoding='utf-8')

final = editor.read_text(encoding='utf-8')
checks = {
    'api root normalization': "configuredUri.replace(path: '', query: null, fragment: null)" in final,
    'basic auth validation': "'Authorization': basicAuthorization" in final,
    'query auth fallback': "'api_key': normalizedApiKey" in final,
    'captcha interceptor': 'customInterceptor: withCaptcha' in final,
    'profile primary proof': "profileResponse = await requestApi('/profile.json')" in final,
    'safe final uri diagnostic': 'safeUri(response.realUri)' in final,
    'html challenge diagnostic': 'La API sigue devolviendo HTML después del chequeo anti-bot' in final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.7 guard failed: {label}')

print('DANBOORU_API_ROOT_NORMALIZED=PASS')
print('DANBOORU_VALIDATION_BASIC_AUTH=PASS')
print('DANBOORU_VALIDATION_QUERY_FALLBACK=PASS')
print('DANBOORU_VALIDATION_CAPTCHA_INTERCEPTOR=PASS')
print('DANBOORU_SAFE_REDIRECT_DIAGNOSTIC=PASS')
print('V8_7_DANBOORU_CHALLENGE_AUTH=PASS')
