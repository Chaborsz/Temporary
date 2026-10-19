from pathlib import Path

editor = Path('lib/src/pages/settings/booru_edit_page.dart')
text = editor.read_text(encoding='utf-8')

start_marker = "  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(\n"
end_marker = "\n  Future<void> _showDanbooruLoginDialog() async {"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('v8.8: could not locate v8.7 Danbooru validator')

new_validator = r'''  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(
    String login,
    String apiKey,
  ) async {
    final enteredLogin = login.trim();
    final normalizedApiKey = apiKey.trim();
    if (enteredLogin.isEmpty || normalizedApiKey.isEmpty) {
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

    final apiRootUri = configuredUri.replace(path: '', query: null, fragment: null);
    final apiRoot = apiRootUri.toString().replaceFirst(RegExp(r'/$'), '');
    final expected = enteredLogin.toLowerCase().replaceAll(' ', '_');

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

    List<Map<dynamic, dynamic>> usersFrom(dynamic raw) {
      final decoded = decodeBody(raw);
      final users = <Map<dynamic, dynamic>>[];
      if (decoded is List) {
        for (final item in decoded) {
          if (item is Map) users.add(item);
        }
      } else if (decoded is Map) {
        if (decoded['users'] is List) {
          for (final item in decoded['users'] as List) {
            if (item is Map) users.add(item);
          }
        }
        if (decoded['user'] is Map) users.add(decoded['user'] as Map);
        if (decoded['data'] is Map) users.add(decoded['data'] as Map);
        if (decoded.containsKey('name')) users.add(decoded);
      }
      return users;
    }

    Map<dynamic, dynamic>? findExactUser(dynamic raw) {
      for (final candidate in usersFrom(raw)) {
        final name = candidate['name']?.toString().trim();
        final actual = (name ?? '').toLowerCase().replaceAll(' ', '_');
        if (name != null && name.isNotEmpty && actual == expected) return candidate;
      }
      return null;
    }

    String safeUri(Uri uri) => '${uri.scheme}://${uri.authority}${uri.path}';

    Dio withCaptcha(Dio dio) =>
        DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent);

    Future<Response<dynamic>> publicUserLookup() {
      return DioNetwork.get(
        '$apiRoot/users.json',
        headers: {
          'User-Agent': Tools.appUserAgent,
          'Accept': 'application/json',
        },
        queryParameters: {
          'search[name_matches]': enteredLogin,
          'limit': 10,
        },
        customInterceptor: withCaptcha,
      );
    }

    Response<dynamic>? publicUsersResponse;
    Map<dynamic, dynamic>? publicUser;
    try {
      publicUsersResponse = await publicUserLookup();
      publicUser = findExactUser(publicUsersResponse.data);
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      return (
        ok: false,
        message: status != null
            ? 'No se pudo comprobar públicamente el username (HTTP $status).'
            : 'No se pudo comprobar públicamente el username: ${e.type.name}.',
        userName: null,
      );
    }

    if (publicUser == null) {
      final suggestions = usersFrom(publicUsersResponse.data)
          .map((user) => user['name']?.toString().trim())
          .whereType<String>()
          .where((name) => name.isNotEmpty)
          .take(5)
          .toList();
      final suggestionText = suggestions.isEmpty ? '' : ' Coincidencias: ${suggestions.join(', ')}.';
      return (
        ok: false,
        message: 'No existe un usuario Danbooru exacto llamado "$enteredLogin".$suggestionText Usa el username de la cuenta, no el email.',
        userName: null,
      );
    }

    final canonicalLogin = publicUser['name']!.toString().trim();
    final canonicalId = publicUser['id']?.toString().trim();
    final basicAuthorization = 'Basic ${base64Encode(utf8.encode('$canonicalLogin:$normalizedApiKey'))}';

    Future<Response<dynamic>> requestAuthenticated(
      String path, {
      Map<String, dynamic>? query,
    }) async {
      try {
        return await DioNetwork.get(
          '$apiRoot$path',
          headers: {
            'User-Agent': Tools.appUserAgent,
            'Accept': 'application/json',
            'Authorization': basicAuthorization,
          },
          queryParameters: query,
          customInterceptor: withCaptcha,
        );
      } on DioException catch (basicError) {
        if (basicError.response?.statusCode != 401) rethrow;
        return DioNetwork.get(
          '$apiRoot$path',
          headers: {
            'User-Agent': Tools.appUserAgent,
            'Accept': 'application/json',
          },
          queryParameters: <String, dynamic>{
            ...?query,
            'login': canonicalLogin,
            'api_key': normalizedApiKey,
          },
          customInterceptor: withCaptcha,
        );
      }
    }

    try {
      final response = await requestAuthenticated('/profile.json');
      final profileUser = findExactUser(response.data);
      if (profileUser != null) {
        final userName = profileUser['name']!.toString().trim();
        final userId = profileUser['id']?.toString().trim();
        return (
          ok: true,
          message: 'Autenticado como $userName${userId?.isNotEmpty == true ? ' (ID $userId)' : ''}.',
          userName: userName,
        );
      }
      return (
        ok: false,
        message: 'El username existe${canonicalId?.isNotEmpty == true ? ' (ID $canonicalId)' : ''}, pero /profile.json no devolvió esa identidad. final=${safeUri(response.realUri)}.',
        userName: null,
      );
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      if (status == 401) {
        return (
          ok: false,
          message: 'El usuario "$canonicalLogin" existe${canonicalId?.isNotEmpty == true ? ' (ID $canonicalId)' : ''}, pero la API Key fue rechazada para esa cuenta. Comprueba que la key pertenece exactamente a ese usuario, que no fue revocada y que copiaste la API Key (no la contraseña de la cuenta).',
          userName: null,
        );
      }
      if (status == 403) {
        return (
          ok: false,
          message: 'El usuario "$canonicalLogin" y la API Key fueron reconocidos, pero la key no permite este endpoint (posible restricción de permisos o IP).',
          userName: null,
        );
      }
      return (
        ok: false,
        message: status != null
            ? 'El usuario "$canonicalLogin" existe, pero la validación autenticada falló con HTTP $status.'
            : 'El usuario "$canonicalLogin" existe, pero la validación autenticada falló: ${e.type.name}.',
        userName: null,
      );
    }
  }
'''

text = text[:start] + new_validator + text[end:]

# Persist the server-canonical username after a successful verification.
text = text.replace(
    'booruUserIDController.text = loginController.text.trim();',
    'booruUserIDController.text = verifiedLogin ?? loginController.text.trim();',
    1,
)
text = text.replace(
    "'“Validar y aplicar” usa el API root, Basic Auth y el mismo chequeo anti-bot que las búsquedas; login + api_key queda como fallback. '",
    "'“Validar y aplicar” comprueba primero que el username exista y luego valida la API Key contra esa cuenta. Usa el username de Danbooru, no el email. '",
)

editor.write_text(text, encoding='utf-8')

final = editor.read_text(encoding='utf-8')
checks = {
    'public username lookup': "Future<Response<dynamic>> publicUserLookup()" in final,
    'public lookup before auth': "publicUsersResponse = await publicUserLookup();" in final,
    'canonical login': "final canonicalLogin = publicUser['name']!.toString().trim();" in final,
    'canonical id': "final canonicalId = publicUser['id']?.toString().trim();" in final,
    'canonical basic auth': "utf8.encode('$canonicalLogin:$normalizedApiKey')" in final,
    'canonical query fallback': "'login': canonicalLogin" in final,
    'specific 401 diagnostic': 'pero la API Key fue rechazada para esa cuenta' in final,
    'specific 403 diagnostic': 'posible restricción de permisos o IP' in final,
    'no email hint': 'Usa el username de la cuenta, no el email.' in final,
    'persist canonical username': 'booruUserIDController.text = verifiedLogin ?? loginController.text.trim();' in final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.8 guard failed: {label}')

print('DANBOORU_PUBLIC_USERNAME_LOOKUP=PASS')
print('DANBOORU_CANONICAL_USERNAME=PASS')
print('DANBOORU_KEY_REJECTION_DIAGNOSTIC=PASS')
print('DANBOORU_PERMISSION_RESTRICTION_DIAGNOSTIC=PASS')
print('V8_8_DANBOORU_IDENTITY_DIAGNOSTIC=PASS')
