# Endurance Stage13 - Experimental global ID2047 freeze-to-zero (x86)

## Scope
Single-player game Forest of the Blue Skin Build29, Pixel Game Maker MV.
Endurance is the pink heart gauge below LIFE and MP.

This is an EXPERIMENTAL DLL TEST. Not yet confirmed to change that HUD gauge.

Evidence: Stage12 EnduranceWriters.log from actual game execution:
- PlayVariableData::setValue: 377,903 calls.
- Global variable ID2047 (temptation gauge, MAX76): 85 calls.
- ID2003: 174, ID2386: 48, ID2054: 8.
- requestValue: zero calls.
- Previous GameManager::assignVariableData hook: zero calls and nonfunctional.

Stage13 intercepts ONLY PlayVariableData::setValue RVA 0x6AB90 and passes
0.0 to the ORIGINAL function when both conditions hold:
- AGTK variable ID at +0x18 is 2047.
- Associated object pointer at +0x60 is null (global variable).

Every other write keeps its original value and original return value.
project.json, player.exe, HP/MP, and other gauge variables are untouched.

## Installation (Windows, x86)
1. Close game. Restore original Resources\data\project.json if the Stage9
   patched project was installed.
2. Back up save games. Remove previous Endurance diagnostic version.dll.
3. If version.dll already existed before our DLLs, do NOT overwrite another mod.
4. Download successful Stage13 GitHub Actions artifact.
5. Extract it. Copy ONLY version.dll next to player.exe.
6. Start game, load a test save and trigger an event that normally increases
   the pink heart gauge (Endurance).
7. Close game and inspect EnduranceFreeze2047.log next to player.exe.
   A genuine runtime interception shows, for example:
   FREEZE_2047_WRITE count=1 requested=75.0000 passed=0.0
   COUNTERS frozen_global_2047 must increase above zero.

## Diagnostic lines
- SOURCE_OK: EXE hash and size match canonical original.
- HOOK_INSTALLED: hook installed, but not proof it was called.
- FREEZE2047_READY: hook prepared to override global ID2047.
- FREEZE_2047_WRITE: confirmed ACTUAL redirected ID2047 write.
- COUNTERS: runtime setValue calls and number of ID2047 changes intercepted.
- HOOK_FAILED: no changes installed.

FREEZE_2047_WRITE proves interception only, NOT that the visible English
Endurance bar corresponds to variable 2047. If the gauge still increases with
the counter above zero, another variable or route may control the HUD.

## Uninstall
Close game, delete ONLY this version.dll, restart.
Never remove real Windows System32\version.dll.

## Warnings
- Not tested in an actual game session. CI tests cover Windows x86
  proxy exports, EXE identity, target bytes, and 8/8 mock-setter cases.
- Forcing temptation thresholds 75/76 to zero may prevent scene progression.
- Use only in single-player with a test save.
- Do not combine with the Stage9 modified project.json.

Source: cheats/endurance/dll/endurance_freeze2047_stage13.cpp
