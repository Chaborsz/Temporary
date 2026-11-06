# Forest of the Blue Skin — Stage44 experimental clone-owned event targeting

## User's Stage43 runtime findings
- Original canonical EXE and all baseline Endurance/clone hooks installed.
- Two optional action hooks refused: `execActionScriptEvaluate` and `execActionSwitchVariableChange` due to absolute relocatable SEH-handler push immediates in the prologue.
- Stage43 captured **direct evidence**: `EVENT_ACTION kind=0 owner_id=1 owner=clone target=original args=313,2 caller_rva=0x1533A7`, while clone instance=315 and original instance=313.
- Other owners ID25 and ID91 also repeatedly target original, and Stage43 reported owner=other with corresponding caller RVAs. Do NOT globally redirect these other actors.
- No conventional `DAMAGE_CALL` or `HP_CHANGE` in earlier Stage41 gameplay log, so an action/variable/script path may be responsible for the event.

## Implementation Stage44
- Adds narrow, experimental redirect in `ObjectAction::getTargetObjectInstanceId` only if ALL conditions hold: clone active, both actors in same tracked scene, resolver OWNER pointer exactly equals the tracked clone, the returned target pointer exactly equals original, requested positive instance ID, scope=2, clone is distinct and actual ObjectData ID1.
- The return is then replaced with the clone pointer and recorded as `CLONE_TARGET_REDIRECT owner=clone ... caller_rva=...`.
- EVERY other resolver call returns its native result unchanged: other actors (enemy/event) and original player; other scopes, zero/negative IDs, unrelated actor IDs, and unknown scenes.
- This **may improve self-owned action/condition targeting of the clone but is not proven to redirect external event attacks**. If the observed event still attacks the original, do NOT extend the redirect to external actors without identifying an event-specific activation path.
- No edits to original `player.exe`, `project.json`, or saves on disk. Uses one local x86 `version.dll`.
- Keeps proven global Endurance ID2047 filter, original/clone physics handling, F9 spawn/remove, F10 removal, player reacquisition after scene changes.

## Important safety correction: ASLR hook preimages
- `ObjectAction::execActionScriptEvaluate` at RVA 0x149980 and `ObjectAction::execActionSwitchVariableChange` at RVA 0x146470 both have a 10-byte instruction-aligned entry `55 8B EC 6A FF 68 <SEH absolute address>`.
- The four-byte immediate at entry+6 is an actual PE HIGHLOW relocation, so raw memcmp with canonical disk bytes fails when ASLR rebases the exe.
- Stage44 builds the exact expected 10-byte preimage using the loaded module base plus fixed RVAs for SEH addresses (0x4BCA9C and 0x4BC894); the hook still REFUSES installation if actual bytes differ.
- Both optional hooks can now install on correctly relocated canonical EXE; they do not alter scripts or values.
- Check log for `HOOK_INSTALLED ObjectAction::execActionScriptEvaluate`, `HOOK_INSTALLED ObjectAction::execActionSwitchVariableChange`, and `EVENT_ACTION_TRACE_READY`. Otherwise do not assume scripts are monitored.

## F9/F10
- F9: toggle one clone. F10: remove. F6 is native restart and remains untouched.

## How to run the experiment
1. Back up save. Close game.
2. Replace only the previous Stage43 `version.dll` with Stage44 `version.dll` beside the original player.exe. Keep `Resources/data/project.json` original.
3. In normal gameplay, spawn with F9; first walk and verify clone movement is still independent.
4. Test a familiar event that previously attacked the original instead of the cloned actor.
5. Compare **which actor visibly receives the event**; even a `CLONE_TARGET_REDIRECT` log does not guarantee final event effect.
6. Remove with F10, close game and provide `EnduranceCloneStage44.log`.
7. Check `CLONE_TARGET_REDIRECT` lines and `EVENT_ACTION kind=2/3` for script/variable side effects.

## Risks and rollback
- Changing targets of clone-owned action-condition checks could alter the clone's scripted behavior, even if event receivers do not change.
- Some events target original through a different external actor. Stage44 deliberately does NOT replace those targets.
- Experimental build, CI/mock validated but not yet tested in actual gameplay. Stop and restore Stage43/Stage34/Stage13 DLL if unexpected behavior occurs.
- If the game crashes, retain prior log and restore proven Stage13 (Endurance only).

## Source
- `experiments/clone_mode/endurance_clone_stage44.cpp`
- `experiments/clone_mode/test_clone_stage44.cpp`
- `.github/workflows/clone-stage44-dll.yml`