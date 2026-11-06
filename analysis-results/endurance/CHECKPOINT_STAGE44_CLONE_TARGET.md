# Forest of the Blue Skin — Stage44 experimental clone-owned target redirection

## Actual Stage43 gameplay evidence (user pasted log)
- Original game PE32 player.exe SHA256 guard PASS and core spawn/movement/reacquisition/Endurance functions continue to work.
- Two optional hooks refused at runtime: `ObjectAction::execActionScriptEvaluate` and `ObjectAction::execActionSwitchVariableChange` (`prologue mismatch`).
- Concrete evidence of player reference: `EVENT_ACTION kind=0 owner_id=1 owner=clone target=original args=313,2 caller_rva=0x1533a7`. Native function `ObjectAction::getTargetObjectInstanceId` resolved original player while action OWNER pointer was spawned clone.
- Other actor owners ID25/91 repeatedly resolve original by instance313. Do not globally change their targets.
- Clone ID1 instances spawned and removed across scenes. Endurance ID2047 freeze logs PASS. No direct damage/HP route conclusively tied to observed events.

## Stage44 static audit findings
- Caller RVA 0x1533a7 = VA 0x005533A7 inside ObjectAction::checkLinkConditionSwitchVariableChanged, which evaluates action-link conditions.
- Caller RVA 0x147087 = VA 0x00547087 inside ObjectAction::execActionSwitchVariableChange; RVA 0x14725e also in the same method.
- Caller RVA 0x13e691 inside ObjectAction::checkActionLinkCondition.
- Two refused hooks' 10-byte prologues contain a `push imm32` operand with actual PE32 HIGHLOW relocation at RVA 0x149986 and RVA 0x146476 respectively. Static bytes cannot be compared raw if ASLR rebases loaded executable.
- SEH handler fixed RVAs 0x4BCA9C and 0x4BC894 are now added to loaded image base when preparing expected preimage; installed trampoline still copies actual relocated bytes and refuses if other bytes mismatch.

## Stage44 native implementation
- Source: experiments/clone_mode/endurance_clone_stage44.cpp
- x86 mock: experiments/clone_mode/test_clone_stage44.cpp
- Workflow: .github/workflows/clone-stage44-dll.yml
- README: experiments/clone_mode/README_CLONE_STAGE44.md
- Inside ObjectAction::getTargetObjectInstanceId only: if action OWNER is exact tracked clone, native selected target is exact tracked original, positive requested instance ID, scope=2, player/clone have separate pointers, same active scene and clone ObjectData ID1, return clone instead. Log `CLONE_TARGET_REDIRECT owner=clone requested=N scope=2 original_to_clone=1 caller_rva=...`.
- Calls for any OTHER action owners, other scope or IDs, or inactive/changed scene preserve native selected target; GameManager object/variable lookups remain unchanged.
- This addresses only clone-OWNED action/condition target lookup, NOT proven to redirect attacks from outside events. Requires user live gameplay confirmation.
- F9 create/remove F10 remove, original F6 restart, movement block, scene player reacquire, Endurance ID2047 freeze are unchanged.
- Legacy `HOOK_INSTALLED ... (read-only)` log corrected to `(guarded x86 hook)` because the Endurance and scoped redirect hooks can actually change values.

## Canonical verified build
- Final GitHub Actions Windows 2022 x86 SUCCESS: https://github.com/Chaborsz/Temporary/actions/runs/42151338082
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/42151338082/artifacts/13472059133
- Artifact ZIP name: Endurance-CloneMode-F9Toggle-F10Remove-TEST-42151338082, 76,927 bytes ZIP (includes Stage44 README).
- Original exe SHA guard, 15 native entrypoint prologues and 2 relocation fixups validated; Windows VERSION export forwarding 10/10 PASS.
- Mock: STAGE44_CLONE_OWNER_REDIRECT_PASS only_clone_owner_same_scene_scope2_no_global; STAGE44_ENDURANCE_CLONE_TEST_PASS; movement filter, scene reacquisition and earlier stage diagnostics PASS.
- This is still EXPERIMENTAL until user visually confirms event recipient in real game.

## Next test
1. Backup save; close game. Replace Stage43 version.dll with Stage44 in original player.exe directory; leave project.json untouched.
2. In normal gameplay F9 spawn clone, then provoke the same event and observe which character receives its consequence.
3. Remove with F10, close and share EnduranceCloneStage44.log.
4. Check successful runtime installation of script/variable hooks and `CLONE_TARGET_REDIRECT` lines. Even if these appear, actual external-event effects could still select original through other owner action.
5. If game fails, close and restore proven Stage34 or Stage13 DLL.

## Robustness
- The local container returned ClientError; as ordered, continued development and build using GitHub rather than stopping.