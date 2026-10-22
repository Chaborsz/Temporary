from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'v8.23 {label}: expected 1 match, found {count} in {p}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print(f'PATCHED v8.23 {label}: {p}')


# ---------------------------------------------------------------------------
# Runtime evidence from v8.22:
# - no slow VISUAL_DB_BATCH remains; idle checkpoints are only 25-36 ms;
# - PAGE_PHASE remains parse_ms=0 / merge_ms=0;
# - TRACKED_BATCH remains 0-7 ms and TAG_BATCH 30-60 ms;
# - the only independent watchdog marker in the supplied tail is
#   WATCHDOG_STALL gap_ms=175 active=page_fetch;
# - RSS is transient rather than monotonic (large peaks later fall), while
#   Flutter ImageCache stays small, so do not shrink the LRU again blindly.
#
# Static inspection found two concrete hot-path defects:
# 1) Tools.checkForCaptcha eagerly calls response.data.toString() before
#    hasCaptchaStrings() can reject hosts with no content signatures. A normal
#    Danbooru JSON page therefore stringifies the complete list/maps/tags on the
#    main isolate even though Danbooru does not use those HTML markers.
# 2) Windows v8.1 enabled target-size decode, exposing an upstream geometry bug:
#    rectangle / landscape staggered targets use width * aspectRatio instead of
#    width / aspectRatio. This can request a decode much larger than the tile.
#
# v8.23 fixes only those two defects and keeps v8.22 DB/memory policy intact.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1) Lazy captcha-content stringification.
# ---------------------------------------------------------------------------
tools = 'lib/src/utils/tools.dart'
replace_once(
    tools,
    """  static bool hasCaptchaStrings(String host, String content) {
    final Map<String, List<String>> knownCaptchaStrings = {
""",
    """  static bool hasCaptchaStrings(String host, Object? content) {
    final Map<String, List<String>> knownCaptchaStrings = {
""",
    'captcha-content-lazy-argument',
)
replace_once(
    tools,
    """    if (stringsToFind == null) return false;
    return stringsToFind.any((t) => content.contains(t));
  }
""",
    """    if (stringsToFind == null) return false;

    // Convert response content to text only after the host is known to use a
    // content signature. Normal JSON APIs (including Danbooru) skip this
    // potentially large synchronous allocation entirely.
    final String contentText = content?.toString() ?? '';
    return stringsToFind.any((t) => contentText.contains(t));
  }
""",
    'captcha-content-stringify-after-host-match',
)
replace_once(
    tools,
    """    return host.contains('booru.allthefallen.moe') &&
        hasCaptchaStrings(host, response.data?.toString() ?? '');
""",
    """    return host.contains('booru.allthefallen.moe') &&
        hasCaptchaStrings(host, response.data);
""",
    'nginx-antiddos-no-eager-response-stringify',
)
replace_once(
    tools,
    """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data.toString() ?? '');
""",
    """    final bool hasCaptchaContent = hasCaptchaStrings(host, response?.data);
""",
    'captcha-check-no-eager-response-stringify',
)


# ---------------------------------------------------------------------------
# 2) Correct Windows thumbnail target-size geometry.
# ---------------------------------------------------------------------------
thumbnail = 'lib/src/widgets/thumbnail/thumbnail.dart'
replace_once(
    thumbnail,
    """    final double widthLimit = constraints.maxWidth * MediaQuery.devicePixelRatioOf(context);
    double thumbRatio = 1;
""",
    """    final double widthLimit = constraints.maxWidth * MediaQuery.devicePixelRatioOf(context);

    // calcThumbWidth can run repeatedly for a recycled/updated tile. Never let
    // a target dimension from the previous layout/item leak into the next one.
    thumbWidth = null;
    thumbHeight = null;

    double thumbRatio = 1;
""",
    'reset-thumbnail-decode-targets',
)
replace_once(
    thumbnail,
    """      case .rectangle:
        thumbRatio = 16 / 9;
        thumbWidth = widthLimit;
        thumbHeight = widthLimit * thumbRatio;
        break;
""",
    """      case .rectangle:
        thumbRatio = 16 / 9;
        thumbWidth = widthLimit;
        thumbHeight = widthLimit / thumbRatio;
        break;
""",
    'rectangle-target-height-ratio-fix',
)
replace_once(
    thumbnail,
    """          } else {
            // horizontal image - resize to height
            thumbHeight = widthLimit * thumbRatio;
          }
        } else {
          thumbRatio = 16 / 9;
          thumbWidth = widthLimit;
          thumbHeight = widthLimit * thumbRatio;
        }
""",
    """          } else {
            // Horizontal tile height is width / (width / height). The previous
            // multiplication could request a decode several times taller than
            // the visible tile on Windows.
            thumbHeight = widthLimit / thumbRatio;
          }
        } else {
          thumbRatio = 16 / 9;
          thumbWidth = widthLimit;
          thumbHeight = widthLimit / thumbRatio;
        }
""",
    'staggered-target-height-ratio-fix',
)


# Guards.
tools_final = Path(tools).read_text(encoding='utf-8')
thumb_final = Path(thumbnail).read_text(encoding='utf-8')
checks = {
    'captcha accepts lazy object': 'static bool hasCaptchaStrings(String host, Object? content)' in tools_final,
    'captcha host checked before stringify': "if (stringsToFind == null) return false;\n\n    // Convert response content" in tools_final,
    'captcha eager stringify removed': "hasCaptchaStrings(host, response?.data.toString() ?? '')" not in tools_final,
    'nginx eager stringify removed': "hasCaptchaStrings(host, response.data?.toString() ?? '')" not in tools_final,
    'captcha response passed lazily': 'hasCaptchaStrings(host, response?.data);' in tools_final,
    'nginx response passed lazily': 'hasCaptchaStrings(host, response.data);' in tools_final,
    'thumbnail targets reset': 'thumbWidth = null;\n    thumbHeight = null;' in thumb_final,
    'rectangle divide ratio': 'thumbHeight = widthLimit / thumbRatio;' in thumb_final,
    'wrong multiply target removed': 'thumbHeight = widthLimit * thumbRatio;' not in thumb_final,
    'Windows target resize retained': '(!PlatformExt.isDesktop || Platform.isWindows)' in thumb_final,
    'Windows thumbnail-only retained': 'if (Platform.isWindows)' in thumb_final and "thumbFolder = 'thumbnails';" in thumb_final,
}
for label, ok in checks.items():
    if not ok:
        raise SystemExit(f'V8.23 guard failed: {label}')

print('V8_23_CAPTCHA_LAZY_RESPONSE_STRINGIFY=PASS')
print('V8_23_DANBOORU_JSON_STRINGIFY_HOTPATH_REMOVED=PASS')
print('V8_23_THUMB_TARGET_RESET=PASS')
print('V8_23_RECTANGLE_TARGET_RATIO_FIX=PASS')
print('V8_23_STAGGERED_TARGET_RATIO_FIX=PASS')
print('V8_23_FETCH_AND_DECODE_TARGET_REDUCTION=PASS')
