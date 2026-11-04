# Endurance — verified Stage 5 (2026-11-04)

## Source
- Release: https://github.com/Chaborsz/Temporary/releases/tag/fobs-build29-endurance-input
- Asset: `project_data.zip` — 10,036,197 bytes; contains `project_decrypted.json` — 301,997,021 bytes.
- Decompressed JSON SHA-256: `2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89`.
- Earlier local decrypted JSON was reportedly 294,287,854 bytes. This is DIFFERENT; do not infer corruption or matching build without comparing source versions.
- GitHub Actions Stage 5: https://github.com/Chaborsz/Temporary/actions/runs/41930559396 — PASS.
- Scope: Endurance = aguante/excitación bar below HP/MP. HP EXCLUDED.

## Confirmed project global variables
| Variable ID | Exact project label | Working translation | Initial value |
|---|---|---|---|
| 2003 | プレイヤー射精ゲージ | Player ejaculation gauge | 0 |
| 2011 | 射精ゲージ格納用 | Gauge stored value | 100 |
| 2047 | ちんこ誘惑ゲージ(MAX76) | Temptation gauge (MAX76) | 0 |
| 2054 | 現在の興奮度 | Current excitement/arousal level | 0 |
| 2386 | プレイヤー射精ゲージ表示用 | Player ejaculation gauge display | 0 |

Variable 2047 memo states `75誘惑限界 (MAX76)で誘惑状態`: level 75 is temptation threshold; MAX76 triggers temptation state. This metadata is a project fact; exact Endurance UI mapping remains UNPROVEN.

## Trace findings
- 141 global variable definitions, 11,172 object-scoped variable definitions examined.
- Numeric literal 2054 occurred 295 times across JSON, including one global variable declaration, scene resets and variable-change operations, object action commands and conditions. Literal total alone DOES NOT establish 295 semantic uses or runtime calls.
- Most frequent literal paths:
  - 218 sceneList.item.children.item.scenePartList.item.actionCommandListObject.158.item.switchVariableReset.item.itemId
  - 44 sceneList.item.scenePartList.item.actionCommandListObject.158.item.switchVariableReset.item.itemId
  - 5 each scene ... commonActionCommandListObject.11/.12/.13 ... switchVariableChange.variableId
  - 3 objectList.item.commonActionSettingList.item.objAction.objCommandList.item.switchVariableChange.variableId
  - 3 objectList.item.commonActionSettingList.item.objActionLink.linkConditionList.item.switchVariableChanged.variableId
- HUD-related actions: `興奮度1` (ID353), `興奮度1(ちんこ誘惑ゲージ` (ID354), `興奮度0` (ID355), from earlier stage-4 scan. Object ownership and write semantics are being investigated.

## Remaining
Identify whether UI Endurance corresponds to arousal level 2054, temptation meter 2047 or ejaculation gauge 2003/2386. Inspect variable write/read operations, the responsible player object and display logic. No patch, tested cheat or runtime conclusion.
