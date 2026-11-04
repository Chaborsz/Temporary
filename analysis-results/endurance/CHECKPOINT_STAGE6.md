# Endurance — static audit STAGE6 (verified)

## Source identity and run
- Engine: AGTK / Pixel Game Maker MV; game: Forest of the Blue Skin.
- Original PE32 `player.exe`: SHA-256 `02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea`.
- Uploaded Release: https://github.com/Chaborsz/Temporary/releases/tag/fobs-build29-endurance-input
- `project_data.zip` size: 10,036,197 bytes. Extracts `project_decrypted.json`: 301,997,021 bytes.
- JSON SHA-256: `2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89`.
- Previous historical JSON size 294,287,854 bytes differs; match of game build not yet established.
- Validated Stage6 workflow PASS: https://github.com/Chaborsz/Temporary/actions/runs/41931327394
- Scope: user's Endurance (aguante/excitacion) gauge below HP and MP, **HP excluded**.

## Confirmed game project variables and interpretations
| ID | Exact name | Evidence | Interpretation |
|---|---|---|---|
| 2003 | プレイヤー射精ゲージ | Writes from player/object and scene action commands; copied to 2386 for gauge display | Player's continuous ejaculation gauge source |
| 2386 | プレイヤー射精ゲージ表示用 | In object ID20 `精液ゲージ左原点`, action ID36: `switchVariableChange` of 2386 has `variableAssignValueType=1`, `assignVariableId=2003`, `variableObjectId=0` | Derived gauge display value |
| 2047 | ちんこ誘惑ゲージ(MAX76) | Memo: `75誘惑限界 / (MAX76)で誘惑状態`; scene object `ちんこ誘惑ゲージ` writes 0, 75 and 76, and many other scene/action writes | Temptation gauge; bounded threshold 75/76 |
| 2054 | 現在の興奮度 | Player object common actions ID353 `興奮度1`, ID354 `興奮度1(ちんこ誘惑ゲージ`, ID355 `興奮度0`. Actions write `1`, `1`, `0` with `variableAssignOperator=0` | Current excitement STATE/FLAG; not yet shown to be a continuous gauge |
| 2011 | 射精ゲージ格納用 | Global initial value 100; many writes in object and scene action commands | Temporary/stored gauge value |

Stage6 scanner measured 20,968 matching change/reset/condition operations spanning five related variables; there are repeated serialized scene commands, so this is **not** a count of distinct runtime execution paths. Stage6 performed no game modification or runtime testing.

## Preliminary conclusion
- Numeric global ID 2054 is not a sensible first choice for a constant/continuous Endurance bar patch because game project actions explicitly set it to 0 or 1.
- IDs 2047 and 2003 are independent bar-like resources; 2386 serves as a display variable fed by 2003. Which one corresponds exactly to the user's HUD label "Endurance" remains **UNPROVEN**.
- A runtime cheat or static patch must not be declared functional before the HUD binding and desired behavior are verified.
- The uploaded asset lives in a **public** GitHub Release; not an appropriate place for copyrighted game assets without redistribution rights.

## Next work
- Correlate actual HUD Endurance label and gauge object with `2047` vs `2003/2386` using scene display paths, project text/image assets, and player object actions.
- Then inspect safe player-only logic for consumption/regeneration in project commands or the relevant engine variable accessors.
- No HP changes, game patches, functional cheats or runtime validation performed.

## Scripts
- `cheats/endurance/correlate_endurance_project.py` — Stage5
- `cheats/endurance/audit_endurance_operations.py` — Stage6
- `.github/workflows/endurance-audit.yml` — CI entry
