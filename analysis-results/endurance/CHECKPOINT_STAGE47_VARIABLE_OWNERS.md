# Forest of the Blue Skin — Stage47 variable ownership diagnostics (verified build)

## User's latest Stage44 log
- All 15 native x86 guarded hooks installed including script and variable action executors.
- Existing Endurance global ID2047 freeze logs active.
- Clone F9 spawns, F10 removal, native movement filter active, scene player reacquisition works.
- CLONE_TARGET_REDIRECT owner=clone requested=312 scope=2 original_to_clone=1 caller_rva=0x1533A7 occurs repeatedly; also caller_rva=0x146B31 inside execActionSwitchVariableChange.
- This proves a selected actor pointer was redirected for the CLONE'S OWN action. It does not confirm external event attacks were redirected to clone; user supplied no visual observation.
- The event action owner_inst=4/6 in Stage44 logging was simply unverified raw Object+0x40C. Stage47 labels owner_field40c to prevent interpreting it as real instance ID.

## Grounded project audit (read-only original 301997021-byte decrypted project)
- Object ID1 `プレイヤー` playable: 462 actions, 1213 action links, 1235 switch/variable-change commands.
- Object ID91 `HPゲージその２` is HP indicator; object ID85 `◆◆敵HPゲージ管理` enemy HP gauge manager; object ID25 `メニューを開く用` menu opener. Their accesses to original player should NOT be globally replaced with clone.
- Object ID195 `★ゾンビ`: 174 actions, 272 action links, 266 switch/variable-change commands. Commands include global vars 2003/2047 and per-player ID1 references with qualifier -2; 18 action links of type objectFound referencing player ID1.
- Game combines per-object player state with shared/global scripted state. Simply replacing one clone-owned action target pointer cannot guarantee effects of external scripts will affect the clone.

## Stage47 implementation
- New source: experiments/clone_mode/endurance_clone_stage47.cpp
- New native mock: experiments/clone_mode/test_clone_stage47.cpp
- README: experiments/clone_mode/README_CLONE_STAGE47.md
- GitHub Actions workflow: .github/workflows/clone-stage47-dll.yml
- Adds diagnostic variable sampling to existing PlayVariableData::setValue, no extra hook. Logs VARIABLE_WRITE id=... owner=global/original/clone old=... requested=... count=... when a clone exists.
- Determines owner by comparing variable+0x60 owner against tracked actor pointers and their own PlayObjectData; never classifies purely by object ID1.
- Logs bounded by variable ID and owner. Range 2000..2400 (and 0..64 for actor-owned system variables).
- Only modifying behavior remains proven Endurance global 2047 freeze and the Stage44 narrow clone-owner action target redirect. All unrelated variables forwarded untouched.
- Existing native F9/F10 clone controls, clone-only movement gate, and scene reacquisition unchanged.

## Build
- Local container.exec repeatedly returned ClientError in this turn. GitHub fallback used immediately rather than stopping.
- Final Windows 2022 x86 GitHub Actions SUCCESS: https://github.com/Chaborsz/Temporary/actions/runs/42153187321
- Canonical artifact ZIP: https://github.com/Chaborsz/Temporary/actions/runs/42153187321/artifacts/13473157025
- Artifact name: Endurance-CloneMode-F9Toggle-F10Remove-TEST-42153187321; ZIP size 76,587 bytes.
- Tested Windows VERSION.dll forward exports 10/10, 15 guarded original game hook entrypoints and ASLR relocation checks, native scope tests.
- STAGE47_VARIABLE_OWNER_DIAGNOSTIC_PASS global_original_clone_bounded_no_mutations, STAGE47_CLONE_OWNER_REDIRECT_PASS, STAGE47_ENDURANCE_CLONE_TEST_PASS.
- Runtime real-game Stage47 not yet tested, and event receiver still unresolved.

## Next test
1. Close game, save backup, keep canonical player.exe and project.json.
2. Replace Stage44 version.dll with Stage47 version.dll next to player.exe.
3. Create clone with F9 and trigger the SAME event that previously affected the original.
4. Verify visually whether clone or original receives it; F10 remove clone.
5. Exit and share EnduranceCloneStage47.log, particularly VARIABLE_WRITE and EVENT_ACTION kind=3 / CLONE_TARGET_REDIRECT lines.
6. Do not widen event redirection to HUD/UI/other actor action owners without concrete dynamic activation evidence.

## Safety
- Stage47 is a diagnostic checkpoint, NOT declared stable and not proven to fix external event recipient.
- Rollback by restoring Stage44, Stage34, or verified Endurance-only Stage13 DLL.