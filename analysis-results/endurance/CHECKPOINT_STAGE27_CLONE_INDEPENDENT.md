# Forest of the Blue Skin — Clone Stage27 controller isolation + F9/F10

**User confirmation:** Stage13 Endurance works in real game; Stage23 clone creates, but is linked to original; user wants separate controls and plain unused F keys.

## Root cause hypothesis and verified engine API
- Both actors created with game object ID1 (operatable), so shared keyboard input is the likely link.
- The engine has a **per-instance** controller setter: PlayObjectData::setControllerId(int), VA 0x0046C500 / RVA 0x6C500.
- Its implementation sets AGTK PlayVariableData system variable ID22 through setValue.
- Object::getControllerId VA 0x00528AA0 / RVA 0x128AA0 and Object::getPlayObjectData VA 0x00431A60 confirmed.
- Object+0x310 holds per-instance PlayObjectData. Stage27 guards against original/clone sharing that pointer.
- Stage26 project inputMapping (33 custom+12 system): no Qt F9/F10 bindings. F6 has engine-side reset and stays untouched.

## Implemented Stage27
- F9 alone toggles spawn/remove; F10 alone requests removal. Ctrl/Shift not required.
- Spawns the existing object ID1 through AGTK native execActionObjectCreateForScript, still eligible for player-like event collisions.
- Immediately sets controller ID to -1 **only** on cloned instance PlayObjectData using native setter.
- Verifies Object::getControllerId(clone) is -1 and Object::getControllerId(original) is unchanged; checks two different play-data pointers.
- On isolation failure, refuses to consider clone independent and requests native disappearance.
- Preserves proven Endurance freeze global ID2047 exactly; other variable values unaffected.
- New log EnduranceCloneStage27.log with CLONE_CONTROLLER_STATE and CLONE_INPUT_INDEPENDENT.
- Does not modify player.exe, project.json or save on disk.

## Compiled artifact / tests
- Source: experiments/clone_mode/endurance_clone_stage27.cpp
- Unit test: experiments/clone_mode/test_clone_stage27.cpp
- Readme: experiments/clone_mode/README_CLONE_STAGE27.md
- Build: https://github.com/Chaborsz/Temporary/actions/runs/42139358698 — SUCCESS.
- Download: https://github.com/Chaborsz/Temporary/actions/runs/42139358698/artifacts/13466930960
- ZIP: Endurance-CloneMode-F9Toggle-F10Remove-TEST-42139358698, 73,402 bytes.
- Win32 VERSION.dll export forwarding PASS; exact player.exe hash and native prologue checks PASS.
- F9 edge-trigger test PASS, no modifier keys.
- Controller isolation test PASS: cloned controller assigned -1, original unchanged, rejects shared PlayObjectData and setter failures.
- Endurance freeze 2 tests and 4 passthrough unchanged; add/remove object tests PASS.

## Runtime validation pending
- Clone controller separation **not yet tested in actual game**. The user should replace Stage23 version.dll with Stage27 version.dll, keep original project.json, test F9/F10 with backup saves and send EnduranceCloneStage27.log.
- Check CLONE_INPUT_INDEPENDENT + CLONE_CONTROLLER_STATE original=N->N clone=N->-1 and whether clone stays in place when the original moves.
- If it still moves, motor may route movement through another path or global actions; do not claim complete independence.
- Other scene scripts may still target all ID1 objects; event independence must be tested.
- Remove Stage27 DLL and restore confirmed Stage13 version.dll to roll back.
- Local container/python returned ClientError in the turn; GitHub used strictly as fallback for binary audit and Windows compilation.