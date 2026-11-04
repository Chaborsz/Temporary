# Endurance audit — checkpoint STAGE3 (2026-11-04)

## Input verification
- Repo: Chaborsz/Temporary (public)
- Input: cheats/endurance/input/player.exe
- Size: 8,757,760 bytes
- SHA-256: 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea
- Engine: Pixel Game Maker MV / AGTK / Cocos2d-x
- Target: Endurance (aguante/excitación HUD bar below HP/MP), **not HP**
- No executable modifications or runtime cheats.

## Verified Actions
- Stage 1: https://github.com/Chaborsz/Temporary/actions/runs/41924536277 (PASS; AUDITED_NO_DIRECT_TERM).
- Stage 2: https://github.com/Chaborsz/Temporary/actions/runs/41925179596 (PASS; AGTK export/call reconnaissance).
- Stage 3: https://github.com/Chaborsz/Temporary/actions/runs/41925378740 (PASS; variable callsites).
- Run artifacts have seven-day retention; scripts and this checkpoint are persistent in the repository.

## Findings
- Source byte identity verified; 11,236 PE exports and 190,578 disassembled instructions.
- No direct symbol/keyword confirmed as Endurance/stamina/excitation/arousal.
- AGTK general variable mechanisms:
  - 0x0046BEE0 PlayObjectData::getVariableData — 21 direct callsites.
  - 0x0046D940 PlayData::getVariableData — 7 direct callsites.
  - 0x0046BF50 PlayObjectData::getVariableDataByName — 4 direct callsites.
  - 0x0046C9F0 PlayObjectData::adjustVariableData — 2 direct callsites.
- 34 directly recognized generic variable-access callsites in stage 3; these are NOT specific to Endurance.
- Several numeric variable IDs appear in generic callsites, e.g. 0x23, 0x13, 0x14, 0x26. Their meanings are UNPROVEN and must not be labeled Endurance.

## Open
- Identify the project-specific game variable ID or object logic used to draw and change the HUD Endurance bar.
- Link script/project data references or controlled runtime gauge changes to the AGTK variable accessors.
- Once correlated, inspect Endurance consumption/regeneration only (exclude HP).
- No verified Endurance patch/cheat; no runtime validation.

## Inputs still missing
- Specific game project data containing variable/object/scene definitions, possibly project.json and content archives/resources.
- Only the original player.exe has been uploaded to GitHub; no game data has been supplied for this workstream.
