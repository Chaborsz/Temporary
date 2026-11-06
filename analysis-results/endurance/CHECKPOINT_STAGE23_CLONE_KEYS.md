# Stage23 — Hotkey fix: do not use F6 (game restart)

User reports **F6 restarts the game**. Stage22 F6/F7 controls must NOT be used.

## Rebuilt integrated Endurance+Clone experiment
- New hotkeys: Ctrl+Shift+F9 spawn one actor ID1; Ctrl+Shift+F10 request removal.
- F6 and F7 are completely absent from the Stage23 hotkey polling source; no interception of native game restart.
- Endurance freeze global variable ID2047 (Stage13 tested working in real game) retained with identical branch semantics.
- Stage22 baseline unaffected; Stage23 is a new source and distinct artifact.
- New log: EnduranceCloneStage23.log.

## Verified build
- GitHub Actions fallback because local container and Python execution returned ClientError.
- Successful workflow: https://github.com/Chaborsz/Temporary/actions/runs/42137004256
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/42137004256/artifacts/13465628083
- Artifact name Endurance-CloneMode-CtrlShiftF9-F10-TEST-42137004256 (73,033 bytes ZIP).
- Original player.exe SHA256 and three hook preimage guards pass.
- Native engine methods and x86 VERSION.dll proxy forwards pass.
- Tests: CLONE_STAGE23_RESERVED_KEYS_PASS NO_F6_NO_F7; CLONE_STAGE23_MODIFIER_CHORDS_PASS; STAGE23_CHORD_GUARD_PASS ctrl_shift_f9_f10 edge_only; STAGE23_ENDURANCE_CLONE_TEST_PASS freeze2 passthrough4 add2 remove2.

## Installation/testing
1. Close game. Replace old Stage22 version.dll with Stage23 version.dll alongside player.exe. Do not install multiple proxies.
2. Keep original Resources/data/project.json. Back up save before test.
3. In normal gameplay, hold Ctrl+Shift and tap F9 to spawn, Ctrl+Shift+F10 to remove.
4. Test Endurance still freezes. Send EnduranceCloneStage23.log and observed effect.
5. Stage23 clone creation remains NOT LIVE-GAME VERIFIED, and a second controllable player could interfere with scene events, camera or control logic.
6. Rollback: close game, remove Stage23 version.dll; restore proven Stage13 version.dll if desired.