# Forest of the Blue Skin — Stage49 (TEST, native event-recipient tracing)

Parent **Stage48**. Canonical player.exe SHA-256:
`02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea`

## Stage48 runtime result (user-confirmed)
- Original still receives all damage and scene events when the clone is targeted.
- No `CLONE_EFFECT_SHIELD_BLOCK` was recorded: the Stage48 narrow shield did NOT intercept those effects.
- Clone-owned `CLONE_TARGET_REDIRECT` was observed (to >=128), without solving the event recipient.
- `Object::damaged` / `PlayObjectData::addHp` did not emit victim logs in this scenario. This is NOT proof of every damage route.
- External action owners 195 (enemy) and 72 appeared, along with 25 menu / 91 HP HUD. Do not redirect them all indiscriminately.

## NEW Stage49 hooks (read-only)
All previously installed Stage48 hooks, F9/F10, native movement gate and Endurance 2047 freeze remain.
- `ObjectAction::getTargetObjectById` RVA 0x14D320.
- `ObjectAction::getTargetObjectByGroup` RVA 0x14D270.
- `ObjectAction::checkLinkConditionObjectHit` RVA 0x154920 (SEH fixup relocation guarded).
- `ObjectAction::checkLinkConditionAttackAreaTouched` RVA 0x14F6D0.
- `ObjectAction::checkLinkConditionObjectFound` RVA 0x151890.
- Additional correlation for setter IDs 2003/2047/2044/2031 and their call sites.

New lines:
- `STAGE49_EXTERNAL_EVENT_TRACE_READY` (all 5 installed).
- `ACTION_TARGET_ARRAY kind=by_id|by_group owner_id=... original=... clone=...`
- `ACTION_LINK_CONDITION kind=object_hit|attack_area_touched|object_found owner=... result=...`
- `EVENT_VARIABLE_ORIGIN id=... action_scope=...`

These **do not** change any target pointers, target arrays, collision results, native variables or switch values. Stage48's restricted shield is retained, but may never trigger on the reported event.

## Reproduce once
1. Exit game, back up saves; leave original player.exe and project.json untouched.
2. Replace only `version.dll` with this TEST build.
3. F9 spawn clone, reproduce a zombie hit/interaction on the clone; note whether original reacted.
4. F10 delete clone, exit game.
5. Send `EnduranceCloneStage49.log` and short visual observation.
6. Analyze true event-route caller and actor identity. An eventual fix must not alter HUD/menu/enemy actions globally.

## Status
PE32 compile and mocks are necessary but cannot validate live gameplay.
If unexpected behavior appears, restore verified Stage48 or earlier DLL.
