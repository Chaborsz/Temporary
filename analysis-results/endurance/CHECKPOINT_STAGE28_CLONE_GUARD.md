# Forest of the Blue Skin — Clone Mode Stage28

## New runtime evidence
- User's Stage27 log: SOURCE_OK, 3 HOOK_INSTALLED, CLONE_MODE_READY, PLAYER_CAPTURED ID1 layer=3.
- On F9 the native game DID spawn the ID1 clone, but Stage27 immediately logged `CLONE_CONTROLLER_REFUSED: original player has no active controller.`, `CLONE_ISOLATION_FAILED`, then `CLONE_ISOLATION_CLEANUP_REQUESTED`, `CLONE_REMOVED_BY_ENGINE`.
- This happened repeatedly. So failure to see a clone is due to erroneous overly strict original controller ID sign check, not failed spawn or failed key hotkey.

## Stage28 change
- `Object::getControllerId` native function can report -1 without proving original player inactive; stage28 **accepts original controller == -1** while still verifying that original/clone have distinct objects and PlayObjectData, original controller remains unchanged, and clone controller becomes -1.
- A new `CLONE_CONTROLLER_NOOP_WARNING` explicitly flags if clone controller already equals -1, because setter may have made no actual change. In that case complete input unlinking is UNPROVEN and must be checked by user, not claimed.
- No change to Endurance global variable ID2047 freeze. F9 toggle, F10 remove; no F6 hook.
- New log `EnduranceCloneStage28.log`. Expected `CLONE_CONTROLLER_ORIGINAL_NEGATIVE`, `CLONE_CONTROLLER_STATE`, `CLONE_CREATED` and potential `CLONE_CONTROLLER_NOOP_WARNING`.
- `CLONE_CONTROLLER_CHECK_PASS` is a check that original state remains unchanged and clone state == -1, not proof of behavioral isolation.

## Build and verification
- Original engine APIs `PlayObjectData::setControllerId`, `Object::getControllerId` reviewed in Stage26 and Stage28 static audit.
- Build workflow https://github.com/Chaborsz/Temporary/actions/runs/42140495195 — SUCCESS.
- Artifact https://github.com/Chaborsz/Temporary/actions/runs/42140495195/artifacts/13467486875
- Artifact name Endurance-CloneMode-F9Toggle-F10Remove-TEST-42140495195, 73,445 bytes ZIP.
- Source `experiments/clone_mode/endurance_clone_stage28.cpp`.
- x86 mocked tests now include original negative controller -1 with clone 0, both -1, distinct PlayObjectData and guarded setter; PASS.
- Original exe SHA256 and Win32 VERSION proxy/export checks PASS, 3 native hooks byte guard PASS.
- Stage28 user runtime validation PENDING. Cloning and controller independence NOT claimed until observed in actual game.

## Installation and rollback
1. Close game, retain original project.json. Back up saves.
2. Replace Stage27 version.dll with Stage28 version.dll next to player.exe.
3. In gameplay press F9; observe if a second actor appears and whether walking still moves both. F9 again or F10 to remove.
4. Send EnduranceCloneStage28.log and describe movement behavior.
5. If crash/glitch, stop game and restore known-working Stage13 Endurance DLL.

## Workspace
- Local container.exec and python.exec both returned ClientError on this turn; GitHub used as execution/compilation fallback only.