# Forest of the Blue Skin — Stage38 event targeting trace

## Confirmed by user
- Stage34: clone spawns and disappears across scenes, PLAYER_REACQUIRED_FROM_SCENE PASS.
- Endurance global ID2047 freeze persists.
- ObjectMovement::move hook intercepts clone movement.
- Events initiated by clone still direct attacks and effects to the original player.
- Root cause likely event target-resolution/global player reference; movement and spawn hooks cannot fix this.

## Static target-resolution findings
- `Scene::getObjectPlayer()` VA 0x00597780, returns player-like object.
- `Scene::getObjectInstance(int objectId,int instanceId,int scope)` VA 0x0059BE80.
- `GameManager::getTargetObjectByInstanceId(int instanceId)` VA 0x005E8470.
- ProjectData::getExpandedText and PlayObjectData::adjustVariableData use Scene::getObjectInstance in static xrefs; blind patch could break text and variable references.
- Direct xrefs to getObjectPlayer are zero in static scan; virtual calls may still occur.
- Redirection to clone is NOT implemented until runtime event-specific caller evidence is available.

## Stage38 diagnostic binary
- Sources: experiments/clone_mode/endurance_clone_stage38.cpp and test_clone_stage38.cpp.
- Guide: experiments/clone_mode/README_CLONE_STAGE38.md.
- Log: EnduranceCloneStage38.log.
- Logs call-site RVA, requested ID/instance and whether return points to ORIGINAL, CLONE, OTHER or NULL.
- Read-only for target selection; it preserves original return pointers and other Stage34 features.
- Hook points: 0x197780, 0x19be80, 0x1e8470 plus all Stage34 hooks.
- Guards: original player.exe SHA256, specific entry bytes, correct Win32 x86 proxy ABI.

## Build / tests
- GitHub Actions SUCCESS https://github.com/Chaborsz/Temporary/actions/runs/42145959980
- Artifact https://github.com/Chaborsz/Temporary/actions/runs/42145959980/artifacts/13469958565
- Artifact name Endurance-CloneMode-F9Toggle-F10Remove-TEST-42145959980.
- Artifact size: 74,407 bytes ZIP.
- Verified 3 new read-only target resolver prologues, original Endurance and movement tests, scene reacquire and add/remove.
- `STAGE38_READ_ONLY_EVENT_RESOLVER_PASS originals_preserved scope_guarded` PASS.
- `VERSION_PROXY_FORWARD_SMOKE_PASS` exports=10 PASS.
- Does NOT establish actual event hit redirection in-game.

## Next user test
1. Backup save, close game, replace Stage34 version.dll with Stage38 version.dll next to player.exe.
2. F9 spawn clone in a scene, allow a few seconds idle.
3. Trigger the exact event which attacks original instead of clone.
4. F10 remove clone; close game; share EnduranceCloneStage38.log.
5. Compare TARGET_RESOLVE callsite RVA and return identity around the event. If no relevant lookup logged, investigate direct script/static action target selection.

## Tool fallback
- Local container.exec returned ClientError. GitHub used as requested fallback to continue working; no early stop.