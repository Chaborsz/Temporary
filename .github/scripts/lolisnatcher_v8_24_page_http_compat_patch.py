from pathlib import Path

p = Path('lib/src/boorus/danbooru_handler.dart')
text = p.read_text(encoding='utf-8')
old = """    return DioNetwork.get(
      uri.toString(),
      headers: requestHeaders,
      queryParameters: requestQueryParams,
      options: fetchSearchOptions(),
      customInterceptor: withCaptchaCheck
          ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
          : null,
    );
"""
new = """    // Normalize the final request variables for the v8.24 watchdog wrapper.
    // v8.5's requestHeaders is equivalent to headers here because verified
    // Danbooru auth no longer places Authorization in getHeaders(); the
    // login/api_key pair lives in requestQueryParams.
    queryParams = requestQueryParams;
    return DioNetwork.get(
      uri.toString(),
      headers: headers,
      queryParameters: queryParams,
      options: fetchSearchOptions(),
      customInterceptor: withCaptchaCheck
          ? (dio) => DioNetwork.captchaInterceptor(dio, customUserAgent: Tools.appUserAgent)
          : null,
    );
"""
count = text.count(old)
if count != 1:
    raise SystemExit(f'v8.24 page-http compat: expected 1 final Danbooru request, found {count}')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

final = p.read_text(encoding='utf-8')
checks = {
    'verified auth state retained': '_hasCompleteApiCredentials' in final,
    'request query construction retained': 'requestQueryParams = <String, dynamic>{' in final,
    'safe request log retained': 'safeHeadersForLog' in final,
    'final query normalized': 'queryParams = requestQueryParams;' in final,
    'v8.24 wrapper anchor available': 'headers: headers,\n      queryParameters: queryParams,' in final,
    'no Basic Authorization restored': "defaultHeaders['Authorization']" not in final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.24 page-http compat guard failed: {label}')

print('V8_24_DANBOORU_REQUEST_SHAPE_COMPAT=PASS')
print('V8_24_VERIFIED_AUTH_SEMANTICS_RETAINED=PASS')
