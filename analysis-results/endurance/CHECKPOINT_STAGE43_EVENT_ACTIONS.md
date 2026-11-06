# Forest of the Blue Skin — Clone Stage43 Event Action Target Trace

## Evidence: user's live Stage41 log
- Correct canonical x86 player.exe SHA guard and all 10 native proxy hooks confirmed installed.
- Endurance global ID2047 filter PASS during gameplay, repeated FREEZE_2047_WRITE.
- F9 cloned playable Object ID1 (instance 315); SceneLayer target list ID1 count=2 original=1 clone=1.
- `TARGET_RESOLVE kind=2 request=313 result=original caller_rva=0x1E7074`, observed in multiple sample counts.
- `TARGET_LIST id=1 count=2 original=1 clone=1 caller_rva=0x1E604E` indicates both actors appear in query results.
- No DAMAGE_CALL and no HP_CHANGE recorded during event. This neither proves no attack nor proves clone is target; suggests action/script path remains to investigate.

## Static audit CLOSED
- RVA 0x1E7074 belongs to `GameManager::getVariableValue`: request 313 accesses object system variable data; it is NOT a victim selection call.
- RVA 0x1E604E belongs to `GameManager::getSwitchVariableDataList`: returns candidate object list to collect variables; it is NOT proof of attack targeting.
- Never globally redirect those two methods because they can affect project logic, player variables, UI, camera.
- Native `ObjectAction::getTargetObjectInstanceId(int,int)` VA 0x0054D420 is called by action commands such as execActionActionExec.
- `ObjectAction + 0x50` is owning actor, per canonical PE disassembly of execAction... methods.
- Stage42 confirmed script, action, switch-variable and object-change entrypoints.

## Implemented Stage43: observe native event action routing, no redirection
- Source: experiments/clone_mode/endurance_clone_stage43.cpp
- Tests: experiments/clone_mode/test_clone_stage43.cpp
- Guide: experiments/clone_mode/README_CLONE_STAGE43.md
- Adds 5 optional guarded hooks:
  * ObjectAction::getTargetObjectInstanceId RVA 0x14D420
  * ObjectAction::execActionActionExec RVA 0x148530
  * ObjectAction::execActionScriptEvaluate RVA 0x149980
  * ObjectAction::execActionSwitchVariableChange RVA 0x146470
  * ObjectAction::execActionObjectChange RVA 0x1401A0
- Logs EVENT_ACTION kind=0..4, owner_id, owner_inst, owner=original/clone/other, selected target, args, caller_rva and per-site counts.
- No modification of target pointers, input, native return values, scripts or project files. Logs are bounded by caller/site.
- Retains Stage41 diagnostics TARGET_LIST, TARGET_RESOLVE, DAMAGE_CALL and HP_CHANGE.
- Retains proven Endurance ID2047 freeze and proven F9/F10 clone spawn/movement suppression/scene reacquisition.

## Build and validations
- Original attempt CI 42149581277 failed with missing TargetName declaration before use; addressed in source and confirmed in rerun.
- Final workflow SUCCESS: https://github.com/Chaborsz/Temporary/actions/runs/42149669415
- Artifact ZIP: https://github.com/Chaborsz/Temporary/actions/runs/42149669415/artifacts/13472275985
- Artifact name Endurance-CloneMode-F9Toggle-F10Remove-TEST-42149669415; ZIP size 76,133 bytes.
- Canonical player.exe SHA256 guard PASS, 15 hook byte preimages PASS, ten VERSION.dll proxy exports PASS, native mocked event target/command calls PASS.
- `STAGE43_EVENT_ACTION_READONLY_PASS original_target_unchanged command_returns` and previous mock suites PASS.
- Actual live event target redirection NOT implemented and NOT confirmed.

## Next live test
1. Close game and back up save; leave original player.exe and project.json unchanged.
2. Replace Stage41 version.dll with Stage43 version.dll next to player.exe.
3. Enter normal gameplay, F9 clone, allow short idle, trigger the exact event that currently affects original not clone, then F10 remove.
4. Close game, send EnduranceCloneStage43.log, specifically EVENT_ACTION lines and any DAMAGE_CALL/HP_CHANGE.
5. Correlate event-specific caller + owner ID with target original; only then design narrowly scoped rewrite.

## Robustness
- Local container.exec returned ClientError; GitHub was used as instructed fallback to continue analysis, coding, compilation and testing.