# Forest of the Blue Skin — Stage34 native player reacquisition

## Runtime evidence received
- Stage31 log: hooks for AGTK setValue, SceneLayer add/remove, and ObjectMovement::move all install.
- CLONE_CREATED instances 316,320,323 and CLONE_REMOVED_BY_ENGINE confirm spawn/teardown.
- CLONE_MOVEMENT_BLOCKED count=1/2/3 for instance 316 confirms movement hook invoked for clone.
- Endurance global 2047 frozen, FREEZE_2047_WRITE messages confirm filter still active.
- After PLAYER_REMOVED_BY_ENGINE the old source set g_playerThread=0 and cleared player references; repeated subsequent F9 returned CLONE_REFUSED: player actor not captured yet.

## Stage34 modifications
- Code: experiments/clone_mode/endurance_clone_stage34.cpp.
- Scene::getObjectPlayer() VA 0x00597780 / RVA 0x197780; native x86 __thiscall, confirmed in canonical original player.exe by export and exact prologue.
- At F9 spawn if cached player missing or scene changed, call Scene::getObjectPlayer() on current scene and validate player ObjectData ID=1, not same pointer as known clone, layer points back to current Scene.
- Restore actor/layer/scene pointer and thread reference only on successful validation; no dangling pointers.
- On PLAYER_REMOVED_BY_ENGINE invalidate all actor references but retain known original game thread ID to safely poll hotkeys.
- If the new scene still has no active player, log pending/refused; never manufacture the player or bypass safety.
- Endurance filter and clone owner-specific movement hook unchanged; F9/F10 unchanged; F6 native reset untouched.
- New log EnduranceCloneStage34.log. Important: PLAYER_REACQUIRED_FROM_SCENE; PLAYER_REACQUIRE_PENDING or REFUSED.

## Workflow / binary
- Workflow SUCCESS: https://github.com/Chaborsz/Temporary/actions/runs/42144426062
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/42144426062/artifacts/13468458168
- Name: Endurance-CloneMode-F9Toggle-F10Remove-TEST-42144426062. ZIP size 73,690 bytes.
- Build x86 DLL and exact player.exe SHA guard PASS.
- All four hook prologues PASS; Scene::getObjectPlayer export and prologue PASS.
- Windows VERSION.dll proxy exports=10 PASS.
- Mock stage34 scene recovery: PASS valid_player_only thread_retained stale_rejected.
- Endurance mock and owner-only movement mock PASS; object add/remove mock PASS.
- Runtime game test for Stage34 not yet done; user to try scene change and F9 and send EnduranceCloneStage34.log.

## Environment
- Local Python/container failed with ClientError. GitHub fallback was explicitly requested and successfully used. Do not halt on future local errors; preserve checkpoint and use GitHub as alternative.