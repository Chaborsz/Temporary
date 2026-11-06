# Forest of the Blue Skin — Clone Stage48 (experimental)
Parent: **Stage47** — canonical player.exe SHA-256 `02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea`.

## Finding from actual Stage47 log
- Clone and original have distinct pointers/runtime data.
- Clone-owned action selection redirects original to clone (observed).
- Yet events on clone **still affect original** (user-confirmed).
- Global variable 2003 changed 19→25→31→37 (+6); global 2047 requests 20/3 were held at zero.
- Other actor owners (ID25 menu, ID91 HUD) legitimately resolve original; their targets must not be rewritten.
- No runtime evidence yet establishes the full external-event path.

## Stage48 targeted change
- Keep Stage47's 15 hooks, F9/F10, 2047 global freeze, movement gate, native action redirect, scene reacquisition.
- Add **thread-local, nested, exact-action-owner scoping** to the four action executor hooks (action, script, variable, object change).
- While **clone-owned** action executes, suppress (a) setters of original player's *local* variables and (b) the observed global variable ID2003 setter; return the pre-write value without calling the native setter.
- Other actor actions, other global variables, clone-local writes, and gameplay without a clone are forwarded unchanged.
- Log `CLONE_EFFECT_SHIELD_READY` and `CLONE_EFFECT_SHIELD_BLOCK id=... owner=original|global`. These establish whether the original bleed is inside the clone-owned executor path.
- **This is a limited experimental fix, not proof of complete external event isolation.** If original still reacts while no shield block is logged, the recipient is chosen by an external owner/other path. Do not globally redirect HUD/monster targeting.

## Install / test
1. Exit game, back up saves, keep original player.exe and project.json unchanged.
2. Replace the prior `version.dll` beside player.exe with Stage48 test DLL.
3. F9 clone; reproduce **the exact same** event that affected original in Stage47; observe who receives it.
4. F10 remove; exit. Provide `EnduranceCloneStage48.log`, especially shield blocks and EVENT_ACTION/VARIABLE_WRITE lines.
5. Restore Stage47 version.dll if unintended behavior occurs.

## CI/mock scope
x86 MSVC /MT DLL; canonical PE hash and guarded prologue checks; VERSION proxy exports and native unit tests. Mock PASS does not establish live gameplay correctness.
