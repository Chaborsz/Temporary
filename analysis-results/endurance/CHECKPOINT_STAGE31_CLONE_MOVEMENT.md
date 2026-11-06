# Forest of the Blue Skin — Stage31 clone movement gate

## Evidence from user Stage28 log
- 3 successful `CLONE_CREATED` for object ID1, instance 315/318/321, level layer 3.
- Clone removal works: `CLONE_DISAPPEAR_REQUESTED`, `CLONE_REMOVED_BY_ENGINE`.
- `CLONE_CONTROLLER_STATE original=-1->-1 clone=-1->-1` and `CLONE_CONTROLLER_NOOP_WARNING` conclusively show the controller setter did not separate movement.
- User reports clone still moves linked with original.
- Endurance freeze continues working: `FREEZE_2047_WRITE`, rising `frozen_global_2047` counters.
- At later scene change, PLAYER_REMOVED_BY_ENGINE and CLONE_REMOVED_BY_ENGINE, then no player captured; Stage31 preserves no-stale-pointer safeguard.

## New static audit
- `ObjectMovement::move(float)` at VA 0x0051A020 (RVA 0x11A020) discovered in the original canonical player.exe.
- Its prologue `53 8b dc 83 ec 08` confirmed; movement owner's Object* is stored in ObjectMovement+0x18.
- x86 MSVC ABI: ObjectMovement in ECX, hidden Vec2 result pointer and float delta on the stack.
- `Object::getInputDirectionId` only returns Object+0x418, `ObjectMovement::getInputDirection` returns stored vectors, but getter interception would not necessarily cover inlined reads. Hook movement function instead.

## Stage31 implementation
- No more attempted changes to system controller ID22. Only checks original and clone have distinct Object and PlayObjectData.
- Adds fourth hook to native `ObjectMovement::move`, to zero returned movement for the tracked clone only; calls original unchanged for player and every other actor.
- Keeps the normal object update, events and scene creation routines running. However gravity/scripted movement may also be blocked; still experimental.
- Freeze of global 2047 from user-proven Endurance Stage13 remains unchanged.
- F9 toggles one clone; F10 remove; native F6 reset not touched.
- Log `EnduranceCloneStage31.log` with `CLONE_MOVEMENT_BLOCKED count=N` to verify real runtime gate.
- `PLAYER_REMOVED_BY_ENGINE` guard preserved for scene transition.
- No modifications of original EXE, project.json or save files on disk.

## Output / validation
- GitHub Actions fallback, because both container and Python local returned `ClientError` in this turn.
- Workflow SUCCESS: https://github.com/Chaborsz/Temporary/actions/runs/42142298734
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/42142298734/artifacts/13466784575
- Artifact name Endurance-CloneMode-F9Toggle-F10Remove-TEST-42142298734, ZIP size 73,484 bytes.
- Source: `experiments/clone_mode/endurance_clone_stage31.cpp`.
- Mock: `experiments/clone_mode/test_clone_stage31.cpp`.
- Instructions: `experiments/clone_mode/README_CLONE_STAGE31.md`.
- PE32 x86 native 4 prologues PASS, Win32 version proxy exports PASS, mock movement clone-only/original-forward/cleanup-forward PASS, Endurance mock PASS.

## Missing
- Real in-game Stage31 behavior NOT yet tested. Need user confirm whether F9 clone remains standing still while player moves and can still trigger events.
- If clone still moves and `CLONE_MOVEMENT_BLOCKED` absent, hook may not receive clone calls; if present then another movement route is responsible.
- On any crash or gameplay problem, close game and restore proven Stage13 DLL or previous Stage28.