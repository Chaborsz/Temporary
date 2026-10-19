from pathlib import Path

editor = Path('lib/src/pages/settings/booru_edit_page.dart')
text = editor.read_text(encoding='utf-8')

# The v8.5 validator assumed /profile.json was always decoded as a top-level
# Map. Runtime testing showed a successful HTTP response whose body had a
# different shape/type, so validate the credential pair primarily through the
# users API and keep /profile.json only as a tolerant fallback.
if "import 'dart:convert';" not in text:
    anchor = "import 'dart:async';\n"
    if text.count(anchor) != 1:
        raise SystemExit(f'v8.6: expected one dart:async import, found {text.count(anchor)}')
    text = text.replace(anchor, "import 'dart:async';\nimport 'dart:convert';\n", 1)

start_marker = "  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(\n"
end_marker = "\n  Future<void> _showDanbooruLoginDialog() async {"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('v8.6: could not locate v8.5 Danbooru validator')

new_validator = r'''  Future<({bool ok, String message, String? userName})> _verifyDanbooruLogin(
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

    final expected = normalizedLogin.toLowerCase().replaceAll(' ', '_');

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
        if (decoded['users'] is List) {
          candidates.addAll(decoded['users'] as List);
        }
        if (decoded['user'] is Map) {
          candidates.add(decoded['user']);
        }
        if (decoded['data'] is Map) {
          candidates.add(decoded['data']);
        }
        if (decoded.containsKey('name')) {
          candidates.add(decoded);
        }
      }

      for (final candidate in candidates) {
        if (candidate is! Map) continue;
        final name = candidate['name']?.toString().trim();
        final actual = (name ?? '').toLowerCase().replaceAll(' ', '_');
        if (name != null && name.isNotEmpty && actual == expected) {
          return candidate;
        }
      }
      return null;
    }

    String responseDescription(Response<dynamic>? response) {
      if (response == null) return 'sin respuesta';
      final contentType = response.headers.value(Headers.contentTypeHeader) ?? 'sin content-type';
      return 'HTTP ${response.statusCode}, ${response.data.runtimeType}, $contentType';
    }

    Map<String, dynamic> authQuery([Map<String, dynamic>? extra]) => <String, dynamic>{
          ...?extra,
          'login': normalizedLogin,
          'api_key': normalizedApiKey,
        };

    Response<dynamic>? usersResponse;
    DioException? usersError;
    try {
      usersResponse = await DioNetwork.get(
        '$baseUrl/users.json',
        headers: {
          'User-Agent': Tools.appUserAgent,
          'Accept': 'application/json',
        },
        queryParameters: authQuery({
          'search[name_matches]': normalizedLogin,
          'limit': 5,
        }),
      );
      final user = findExactUser(usersResponse.data);
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
      usersError = e;
      if (e.response?.statusCode == 401) {
        return (
          ok: false,
          message: '401: Login o API Key incorrectos, o la API Key no pertenece a ese usuario.',
          userName: null,
        );
      }
    }

    // Compatibility fallback for older/nonstandard Danbooru forks. Accept a
    // direct user object, a one-item list, or common {user: ...}/{data: ...}
    // wrappers. Also decode JSON manually if Dio received it as text.
    Response<dynamic>? profileResponse;
    DioException? profileError;
    try {
      profileResponse = await DioNetwork.get(
        '$baseUrl/profile.json',
        headers: {
          'User-Agent': Tools.appUserAgent,
          'Accept': 'application/json',
        },
        queryParameters: authQuery(),
      );
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

    final usersStatus = usersError?.response?.statusCode;
    final profileStatus = profileError?.response?.statusCode;
    if (usersStatus == 403 || profileStatus == 403) {
      return (
        ok: false,
        message: '403: las credenciales llegaron al servidor, pero la API Key o la cuenta no permiten el endpoint de validación.',
        userName: null,
      );
    }

    final usersInfo = usersError != null
        ? 'users: HTTP ${usersError.response?.statusCode ?? '?'}'
        : 'users: ${responseDescription(usersResponse)}';
    final profileInfo = profileError != null
        ? 'profile: HTTP ${profileError.response?.statusCode ?? '?'}'
        : 'profile: ${responseDescription(profileResponse)}';
    return (
      ok: false,
      message: 'El servidor respondió pero no permitió identificar al usuario. $usersInfo; $profileInfo.',
      userName: null,
    );
  }
'''

text = text[:start] + new_validator + text[end:]
text = text.replace("statusMessage = 'Validando /profile.json…';", "statusMessage = 'Validando credenciales…';")
text = text.replace(
    "'“Validar y aplicar” consulta /profile.json con esas credenciales. '",
    "'“Validar y aplicar” comprueba Login + API Key contra la API de usuarios y usa /profile.json solo como fallback. '",
)
editor.write_text(text, encoding='utf-8')

final = editor.read_text(encoding='utf-8')
checks = {
    'dart convert import': "import 'dart:convert';" in final,
    'users validator': "'$baseUrl/users.json'" in final,
    'complete auth pair': "'login': normalizedLogin" in final and "'api_key': normalizedApiKey" in final,
    'profile compatibility fallback': "'$baseUrl/profile.json'" in final,
    'manual JSON decode': 'jsonDecode(body)' in final,
    'list and wrapper parsing': "decoded['users'] is List" in final and "decoded['user'] is Map" in final,
    'safe diagnostics': 'response.data.runtimeType' in final,
    'no old profile-only message': 'El servidor no devolvió un perfil de usuario válido.' not in final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.6 guard failed: {label}')

print('DANBOORU_USERS_LOGIN_VALIDATION=PASS')
print('DANBOORU_PROFILE_FALLBACK=PASS')
print('DANBOORU_TEXT_JSON_DECODE=PASS')
print('DANBOORU_RESPONSE_SHAPE_DIAGNOSTIC=PASS')
print('V8_6_DANBOORU_LOGIN_VALIDATION=PASS')
