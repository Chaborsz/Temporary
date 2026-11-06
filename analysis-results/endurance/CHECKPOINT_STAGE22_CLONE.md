# Endurance + Clone Mode Stage22 — checkpoint

Status: Endurance Stage13 confirmed WORKING by user in game. Stage22 clone EXPERIMENTAL, not yet validated in game.

## Artifact
- CI run: https://github.com/Chaborsz/Temporary/actions/runs/42134707913 — SUCCESS
- Download: https://github.com/Chaborsz/Temporary/actions/runs/42134707913/artifacts/13464304809
- Name: Endurance-CloneMode-F6-F7-TEST-42134707913; ZIP size 72,950 bytes.
- Source: experiments/clone_mode/endurance_clone_stage22.cpp
- Test: experiments/clone_mode/test_clone_stage22.cpp
- Instructions: experiments/clone_mode/README_CLONE_STAGE22.md
- Only the new version.dll replaces the previous Stage13 version.dll; cannot install both.

## Proven static facts
- Player ID1 = プレイヤー, operatable=true; game project has 91 existing native objectCreate commands targeting ID1.
- AGTK native ObjectAction::execActionObjectCreateForScript at VA 0x0053FCF0 takes (int objectId,int x,int y,int layerId), returns instance ID.
- ObjectData ID is at +0x18, ObjectData pointer at Object+0x28C.
- SceneLayer pointer at Object+0x308; SceneLayer scene at +0x290 and layer ID at +0x2B8.
- Object::getPosition at 0x00527D50; GameManager::getInstance at 0x005D32D0.
- Native ObjectAction::execActionDisappear delegates to Object vtable +0x55C with argument true; used by F7.
- The Endurance setter remains PlayVariableData::setValue RVA 0x6AB90, suppressing only global variable 2047 writes.

## CI validation
- WIN32 x86 VERSION.dll compiles and proxies 10 Windows API exports.
- Original player.exe SHA256 guard PASS and 3 hook entrypoint byte guards PASS.
- Native spawn/delete symbols and two folded getter bodies validated.
- 8 isolated mock calls PASS: two Endurance writes frozen; four unrelated value writes forwarded; player/clone capture twice; game removal twice.
- No real gameplay clone runtime test. No project.json or player.exe modifications in the delivered ZIP.

## Controls / log / safety
- F6 spawn one clone at x+56, y on same scene/layer.
- F7 use game disappearance to remove tracked clone.
- Log EnduranceClone.log with SOURCE_OK, CLONE_MODE_READY, PLAYER_CAPTURED, CLONE_CREATED, CLONE_DISAPPEAR_REQUESTED/CLONE_REMOVED_BY_ENGINE, FREEZE_2047_WRITE.
- Risk: second operatable player may share input, interfere with events or camera, or F7 may not remove correctly.
- Use disposable save, close game to roll back by deleting only new version.dll and restoring proven Stage13 DLL.
- If player not captured after load, enter another gameplay scene before F6.

## Environment
- Local container and Python both returned ClientError. GitHub Actions used only as compilation fallback, per user instruction.