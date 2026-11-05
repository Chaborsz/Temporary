# Endurance — Stage13 Freeze2047 using verified PlayVariableData::setValue

Date: 2026-11-05.

## Actual user runtime evidence (Stage12)
The original game with diagnostic DLL returned:
- SOURCE_OK (canonical player.exe SHA256 matches).
- Hooks installed: PlayVariableData::setValue RVA 0x6AB90 and requestValue RVA 0x6ACB0.
- Final COUNTERS set=377903, request=0.
- set2047=85, set2047Global=85, set2047Object=0.
- set2003=174, set2386=48, set2054=8.
- FIRST_SET id2047 object=0 input=75.0000.
Thus the previous assignVariableData hook that observed zero calls was the wrong interception route. The real setter is now validated as called during gameplay. However the precise English Endurance HUD mapping to 2047 is still unproven.

## Stage13 output (experimental)
- Source: cheats/endurance/dll/endurance_freeze2047_stage13.cpp
- Workflow: https://github.com/Chaborsz/Temporary/actions/runs/42130095161
- Result: SUCCESS.
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/42130095161/artifacts/13461949360
- Artifact name: Endurance-Stage13-Freeze2047-x86-TEST-42130095161 (69,804 bytes ZIP)
- version.dll inside: 118,784 bytes, PE32 x86.
- In-process method target: PlayVariableData::setValue, RVA 0x6AB90.
- Only if variable->id at +0x18 equals 2047 AND object pointer at +0x60 is null, original setValue receives value 0.0.
- All other original value inputs/returns pass unchanged; HP, MP, 2003, 2386, 2054 explicitly excluded.
- requestValue not hooked in Stage13.
- Original player.exe and project.json remain unchanged on disk.
- Only valid for 8,757,760-byte canonical player.exe with SHA256 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea.
- Original prologue guard required: 55 8B EC 83 E4 F8.

## CI evidence
- STAGE13_CANONICAL_EXE_PASS
- STAGE13_DLL_X86_EXPORTS_PASS 10
- STAGE13_HOOK_SCOPE_PASS global2047_only
- VERSION_PROXY_FORWARD_SMOKE_PASS exports=10
- STAGE13_FREEZE2047_FILTER_PASS 8/8 writes, 3 frozen, 5 passthrough
- FREEZE_2047_WRITE count=1 requested=75.0000 passed=0.0 (mock)
- STAGE13_DLL_BUILD_AND_FILTER_PASS

## Remaining runtime validation
- Must test on user game. Need EnduranceFreeze2047.log:
  SOURCE_OK, HOOK_INSTALLED PlayVariableData::setValue, FREEZE2047_READY,
  FREEZE_2047_WRITE count >= 1, COUNTERS frozen_global_2047 > 0.
- Even positive counters only prove that global 2047 writes are blocked, not that the pink heart Endurance bar has changed.
- Events requiring temptation gauge 75/76 may break: test on backup save.
- Restore original Resources/data/project.json if user installed Stage9; remove previous version.dll and replace with Stage13 DLL. Never overwrite another mod's pre-existing version.dll.
- Uninstall by closing game and deleting only this proxy version.dll.

## Workspace decision
Local container.exec and python.exec both failed on this turn with ClientError / failed to start. GitHub Actions used solely as compiler fallback. Source artifacts were inspected via connected repository; no new user game files requested. Local environment remains primary when available.
