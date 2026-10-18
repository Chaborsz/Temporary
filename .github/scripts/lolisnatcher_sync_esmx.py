from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

CONSTANTS = Path("lib/src/data/constants.dart")
BASE_PATH = Path("assets/i18n/en.json")
ESMX_PATH = Path("assets/i18n/es-MX.json")


def poeditor_post(endpoint: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.poeditor.com/v2/{endpoint}",
        data=body,
        method="POST",
        headers={"User-Agent": "LoliSnatcher-Windows-Builder/4"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def flatten_keys(value, prefix=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten_keys(child, prefix + (key,))
    else:
        yield ".".join(prefix)


def nested_get(value: dict, dotted: str):
    current = value
    for part in dotted.split("."):
        current = current[part]
    return current


def nested_set(value: dict, dotted: str, leaf) -> None:
    parts = dotted.split(".")
    current = value
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise KeyError(dotted)
        current = child
    current[parts[-1]] = leaf


def nested_delete(value: dict, dotted: str) -> None:
    parts = dotted.split(".")
    current = value
    parents = []
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise KeyError(dotted)
        parents.append((current, part, child))
        current = child
    if parts[-1] not in current:
        raise KeyError(dotted)
    del current[parts[-1]]
    for parent, part, child in reversed(parents):
        if child:
            break
        del parent[part]


constants = CONSTANTS.read_text(encoding="utf-8")
project_match = re.search(r"poeditorProjectId\s*=\s*(\d+)", constants)
token_match = re.search(r"poeditorApiKey\s*=\s*'([^']+)'", constants)
if not project_match or not token_match:
    raise SystemExit("Could not resolve the upstream POEditor project/read-only token")
project_id = project_match.group(1)
api_token = token_match.group(1)

languages = poeditor_post(
    "languages/list",
    {"api_token": api_token, "id": project_id},
)
spanish_mx = next(
    (
        item
        for item in languages["result"]["languages"]
        if item.get("code", "").lower() == "es-mx"
    ),
    None,
)
if spanish_mx is None:
    raise SystemExit("POEditor language es-mx was not found")

percentage = float(spanish_mx.get("percentage") or 0)
remote_count = int(spanish_mx.get("translations") or 0)
if percentage < 99.5:
    raise SystemExit(
        f"POEditor es-mx is not complete enough: {percentage}% ({remote_count} translations)"
    )

export_response = poeditor_post(
    "projects/export",
    {
        "api_token": api_token,
        "id": project_id,
        "language": "es-mx",
        "type": "key_value_json",
    },
)
export_url = export_response.get("result", {}).get("url")
if not isinstance(export_url, str) or not export_url.startswith("https://"):
    raise SystemExit("POEditor did not return a valid es-MX Key-Value JSON export URL")

with urllib.request.urlopen(export_url, timeout=60) as response:
    exported_bytes = response.read()
try:
    esmx = json.loads(exported_bytes.decode("utf-8-sig"))
except Exception as exc:
    raise SystemExit(f"Could not parse POEditor es-MX Key-Value JSON export: {exc}")
if not isinstance(esmx, dict):
    raise SystemExit("POEditor es-MX Key-Value JSON export root is not an object")

base = json.loads(BASE_PATH.read_text(encoding="utf-8"))
base_terms = list(flatten_keys(base))
exported_terms = list(flatten_keys(esmx))
base_set = set(base_terms)
exported_set = set(exported_terms)
missing = sorted(base_set - exported_set)
extra = sorted(exported_set - base_set)

# POEditor counts a pluralized translation as one project term, while a
# Key-Value JSON export expands its plural forms into several leaf keys. The
# project translation count therefore cannot be compared to JSON leaf count.
# Validate the actual source-compatible keyset instead.

# POEditor can be slightly ahead of the exact source commit being built. Ignore
# only keys absent from this commit's English base; they cannot be referenced
# by generated localization code for this revision.
for key in extra:
    nested_delete(esmx, key)

# Spanish cardinal plurals do not use the CLDR `few` category, so POEditor
# omits those leaves from its Spanish export even though the base Slang schema
# keeps them. Complete only `few` by copying the translated Spanish `other`
# sibling for the same message; never fall back to English.
compatibility_aliases = []
for key in missing:
    if not key.endswith(".few"):
        raise SystemExit(
            f"Live es-MX is missing a non-plural-compatibility key: {key}"
        )
    other_key = key[:-4] + ".other"
    try:
        other_value = nested_get(esmx, other_key)
    except (KeyError, TypeError):
        raise SystemExit(
            f"Live es-MX is missing {key} and has no Spanish sibling {other_key}"
        )
    if not isinstance(other_value, str) or not other_value.strip():
        raise SystemExit(
            f"Spanish sibling used for compatibility is empty: {other_key}"
        )
    nested_set(esmx, key, other_value)
    compatibility_aliases.append((key, other_key))

final_terms = list(flatten_keys(esmx))
final_set = set(final_terms)
final_missing = sorted(base_set - final_set)
final_extra = sorted(final_set - base_set)
if final_missing or final_extra:
    raise SystemExit(
        f"Final es-MX keyset mismatch: missing={len(final_missing)} extra={len(final_extra)}"
    )

if nested_get(esmx, "locale") != "es-MX":
    raise SystemExit(f"Unexpected es-MX locale value: {nested_get(esmx, 'locale')!r}")

required_checks = (
    "settings.title",
    "settings.language.title",
    "settings.webview.openWebview",
    "webview.title",
)
for key in required_checks:
    value = nested_get(esmx, key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"Live es-MX required translation is empty: {key}")
    base_value = nested_get(base, key)
    if value == base_value:
        raise SystemExit(
            f"Live es-MX required translation unexpectedly equals English base: {key}={value!r}"
        )

ESMX_PATH.write_text(
    json.dumps(esmx, ensure_ascii=False, indent=4) + "\n",
    encoding="utf-8",
)

print(f"LIVE_ES_MX_PERCENTAGE={percentage:g}")
print(f"LIVE_ES_MX_REMOTE_TRANSLATIONS={remote_count}")
print(f"LIVE_ES_MX_EXPORTED_LEAVES={len(exported_terms)}")
print(f"LIVE_ES_MX_IGNORED_FUTURE_TERMS={len(extra)}")
for key in extra:
    print(f"LIVE_ES_MX_IGNORED_FUTURE_TERM={key}")
print(f"LIVE_ES_MX_COMPATIBILITY_ALIASES={len(compatibility_aliases)}")
print(f"LIVE_ES_MX_FINAL_TERMS={len(final_terms)}")
print(f"LIVE_ES_MX_BASE_TERMS={len(base_terms)}")
print(f"LIVE_ES_MX_UPDATED={spanish_mx.get('updated')}")
for key in required_checks:
    print(f"LIVE_ES_MX_CHECK {key}={nested_get(esmx, key)}")
print("LIVE_ES_MX_KEYSET_MATCH=PASS")
print("LIVE_ES_MX_SYNC=PASS")