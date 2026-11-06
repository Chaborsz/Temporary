# Stage47 — Diagnostic: variable ownership of original/clone/global

## Real Stage44 evidence
- 15 native hooks installed. Redirection occurs for clone-owned action when it targets original, including caller RVAs 0x1533A7 and 0x146B31.
- This is NOT proof that external event effects have moved to clone: there was no visual report yet.

## Original project facts (read only)
- Player object ID1 has 462 actions, 1213 links, 1235 variable/switch commands.
- Object ID91 is the second HP indicator; ID85 manages enemy HP indicators; ID25 opens menu. Their global player lookups must remain untouched.
- Object ID195 (zombie) has 266 variable/switch commands, including per-player ID1 and shared/global variables 2003 and 2047.
- This project uses per-object player state AND globally shared event variables. Target pointer substitution alone does not ensure that every event's consequences select the clone.

## Stage47 change
- Preserves all Stage44 Endurance, scoped owner-only action redirect, native clone spawn/removal, per-clone movement gate, scene recovery, F9/F10, and x86 guarded hooks.
- Adds owner-aware bounded read-only variable telemetry within the existing PlayVariableData::setValue hook.
- Reports VARIABLE_WRITE id=N owner=global|original|clone old=... requested=... count=... for relevant variables only while clone is active.
- Compares variable owner against each actor pointer and PlayObjectData pointer; does not infer owner from object ID1.
- The baseline global ID2047 Endurance freeze continues to 0; all other writes call original setter unchanged.
- Log field owner_inst is renamed owner_field40c because +0x40C is not verified to be an actual instance ID.
- No new native hooks or original game asset modifications.

## Installation and test
1. Exit game and back up saves. Keep canonical player.exe and project.json intact.
2. Replace Stage44 version.dll with Stage47 version.dll beside player.exe.
3. F9 spawn clone; allow a familiar event to activate. Observe which actor actually receives the event.
4. F10 remove clone; exit and send EnduranceCloneStage47.log.
5. Correlate VARIABLE_WRITE owner=global/original/clone with event action kind3 and CLONE_TARGET_REDIRECT.
6. If effects still apply to original, identify the specific script/variable chain without redirecting unrelated HUD, menu, enemy, or camera accesses.

## Status and safety
- Experimental telemetry, not an established fix for event receivers.
- If game behaves unexpectedly, close and restore Stage44 or verified Stage13 Endurance DLL.

## Sources
- experiments/clone_mode/endurance_clone_stage47.cpp
- experiments/clone_mode/test_clone_stage47.cpp
- .github/workflows/clone-stage47-dll.yml