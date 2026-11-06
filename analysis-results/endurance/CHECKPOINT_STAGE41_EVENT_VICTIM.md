# Forest of the Blue Skin — Stage41, victim-side event target diagnosis

## Real game log supplied by user (Stage38)
- Hooks for original Endurance, clone spawn/delete, per-clone movement and 3 read-only scene/instance target resolvers installed.
- Clone ID1 spawned as instance 315; original player was instance 313.
- TARGET_RESOLVE kind=2 request=313 result=original caller_rva=0x1e7074 (site hits 1,2,16,128).
- No kind0/kind1 target lookups were observed in the sent log.
- Clone and Endurance systems remain active; freeze2047 writes are logged.

## Stage39 finding CLOSED
- caller RVA 0x1E7074 = VA 0x005E7074 inside GameManager::getVariableValue, exported at VA 0x005E6D40.
- Disassembly: GameManager::getVariableValue retrieves the object instance ID from system variable 0x26, calls getTargetObjectByInstanceId(313), then reads variable value via PlayObjectData::getVariableData and PlayObjectData::adjustVariableData.
- This observed query is a VARIABLE READ, NOT proof that getTargetObjectByInstanceId is responsible for the attack target.
- Therefore do not globally replace requested instance313 with cloned instance315.

## Stage40 static audit
- Native GameManager::getTargetObjectListByObjectId at VA 0x005E8500. It is called by calcObjectActionProgram and may be involved in actor action targeting.
- Native Object::damaged(Object*,PlayObjectData*,PlayObjectData*) at VA 0x0052F760; native PlayObjectData::addHp(double) at VA 0x0046C670.
- Three additional native hook prologues confirmed in original canonical player.exe.

## Stage41 source / new diagnostic
- Source: experiments/clone_mode/endurance_clone_stage41.cpp
- Mock: experiments/clone_mode/test_clone_stage41.cpp
- Guide: experiments/clone_mode/README_CLONE_STAGE41.md
- Adds read-only target-list, damaged, and HP-effect interceptors. They log which object is victim/attacker, which instance received HP, and target list membership/caller RVA.
- Callsite+object-ID-target-list logs bounded by first two calls and powers, independent of global call count; avoids losing rare event sites.
- Does not modify or redirect recipients or HP. The preexisting proven Endurance global2047 freeze remains ACTIVE and unchanged.
- Retains F9 toggle, F10 remove, clone per-instance movement gating, scene transition player reacquisition.
- New runtime log: EnduranceCloneStage41.log. Search TARGET_LIST, DAMAGE_CALL, HP_CHANGE, TARGET_RESOLVE.

## Compile/tests
- Initial build PASS 42147680478, subsequently refined callsite sampling.
- Latest final build PASS https://github.com/Chaborsz/Temporary/actions/runs/42148023690
- Latest artifact https://github.com/Chaborsz/Temporary/actions/runs/42148023690/artifacts/13470364025
- Artifact name Endurance-CloneMode-F9Toggle-F10Remove-TEST-42148023690, ZIP 75,684 bytes.
- Validations: Win32 PE32 exports PASS (10), 10 hook prologue guards PASS, original EXE SHA guard PASS, correct ABI and return preservation PASS.
- Unit test STAGE41_VICTIM_HP_TARGET_LIST_READONLY_PASS no_return_change scoped_logs; Stage38+Endurance/clone tests also PASS.
- Real in-game Stage41 victim-side events still PENDING: cannot yet claim the attack is redirected to the cloned character.

## Next user test
1. Close game and preserve backup save and project.json original.
2. Replace old Stage38 version.dll with Stage41 version.dll next to player.exe; do not install both.
3. F9 spawn clone. Trigger the same event that previously attacked the original player. F10 remove.
4. Send EnduranceCloneStage41.log. Determine whether the effect uses Object::damaged, PlayObjectData::addHp, or an event action path. If none trace, investigate script-command targeting rather than patching generic variables.

## Workspace preference
- Local container.exec returned ClientError. GitHub fallback correctly used for static analysis and Windows x86 build; local remains primary whenever usable.