# Endurance / temptation candidate — STAGE7 verified

## Source and execution

- Project: Forest of the Blue Skin, Pixel Game Maker MV / AGTK.
- User's objective: "Endurance" = aguante/excitación meter below HP and MP, HP not in scope.
- Source: uploaded `project_data.zip` GitHub Release `fobs-build29-endurance-input`, extracted `project_decrypted.json` (301,997,021 bytes).
- Stage 7 workflow: https://github.com/Chaborsz/Temporary/actions/runs/41932238527 — **PASS**.
- Script: `cheats/endurance/confirm_endurance_hud.py`.
- Source game files were only read, not modified.

## Verified candidate

Global variable **ID 2047** `ちんこ誘惑ゲージ(MAX76)` ("temptation gauge", documented maximum 76).

- Its global-variable memo states 75 is the temptation threshold, 76 enters the temptation state.
- **Object ID 49** named `UIちんこ誘惑ゲージ` ("UI temptation gauge") contains conditions that reference variable ID 2047.
- Stage 7 found **160** such `switchVariableChanged` conditions in object ID 49; the repeated serialized actions are not 160 distinct runtime invocations.
- Stage 7 found 9,529 serialized change/condition occurrences referencing 2047 across scenes and objects, including player and monster actions.
- Examples: `★森の住人` uses `switchVariableChange` on 2047 with operand 30; `★ゾンビ` with operand 5; player-associated scene actions also change 2047. This supports a gameplay-fed gauge.
- Therefore 2047 is a *real value used by a rendered temptation gauge*, not just a Boolean flag.

## Differentiation

- `2054` `現在の興奮度` ("current excitement") is written with 0/1 in player actions and represents an arousal state/flag.
- `2003` `プレイヤー射精ゲージ` is the player ejaculation gauge. Stage 7 found 9,303 serialized change/condition occurrences.
- `2386` `プレイヤー射精ゲージ表示用` is a display mirror for 2003 in object ID20 `精液ゲージ左原点`; read/write relation confirmed.

## Current conclusion

**2047 is high-confidence temptation meter candidate, and UI object 49 definitely reacts to it.**
User reports Endurance is the meter beneath HP/MP. The visual text/physical position "Endurance" has not yet been matched to object ID49, so do not claim the identity is 100% proven. The next confirmatory step is matching the screenshot/HUD location or tracing the relevant UI prefab's screen coordinates to object 49. No patch, freeze or cheat has been created or runtime-tested.

## Canonical refs

- Stage 6: `analysis-results/endurance/CHECKPOINT_STAGE6.md`
- Stage 7: `.github/workflows/endurance-audit.yml` and run 41932238527
