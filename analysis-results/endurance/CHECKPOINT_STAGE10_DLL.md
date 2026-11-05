# Endurance 2047 — Stage 10 DLL experimental

## Artifact and validation (2026-11-05 UTC)

- **Download artifact:** https://github.com/Chaborsz/Temporary/actions/runs/41952938879/artifacts/13382490382
- Workflow: https://github.com/Chaborsz/Temporary/actions/runs/41952938879
- Result: **SUCCESS**.
- Artifact name: Endurance-2047-VERSION-DLL-TEST-41952938879; artifact ZIP size 52,532 bytes.
- DLL inside: version.dll, 91,136 bytes, PE32 i386 Windows DLL, MSVC x86 static CRT.
- Other contents: installation and rollback instructions (README.md).
- Runtime smoke test against a Windows system versioned executable: **PASS**.
- Function forwarders: 10 version.dll Win32 exports, including the original game's three required direct imports: **PASS**.
- Guard when loaded by an unrelated process: **PASS**, hook disabled.
- Target exe hash validation in source: sha256 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea.
- Target RVA: 0x1E8760, GameManager::assignVariableData; original six-byte prologue 55 8B EC 83 E4 C0: **PASS**.
- Original-call x86 fastcall/thiscall ABI smoke tests: **PASS**, 7/7 cases.
  - Global ID2047 with assignment/add/subtraction becomes assign 0.0.
  - ID2003, ID2054 and object-scoped ID2047 are forwarded unchanged.
  - Null variable pointer forwarded unchanged.

## Scope

- Does not modify or replace game project.json or player.exe on disk.
- At runtime it intercepts the code of GameManager::assignVariableData in memory, only for global PlayVariableData ID2047 with no associated object.
- No other variable targeted; HP, MP, ejaculation (2003/2386), excitement flag (2054) stay unchanged.
- Proxy loads the real System32\version.dll and relays the system APIs.
- Only enables hook for exact canonical game executable. If size/hash mismatches, proxy still relays Windows functions but doesn't hook.

## Outstanding / Important

**NOT RUNTIME-VERIFIED WITH THE ACTUAL GAME CLIENT.** Automated tests validate the binary and mock hook behavior, not live game behavior.
- Some assignments may bypass GameManager::assignVariableData; results could be incomplete.
- Scene progression may require the temptation meter to reach 75/76; constant zero could interfere.
- The HUD English label "Endurance" remains not visually matched to UI object49, despite strong variable evidence.
- Remove local version.dll and restart the game to reverse the mod.
- If another mod already supplies version.dll, do not overwrite it; this proxy cannot be safely combined by simple file replacement.
- For testing, first restore the *original* project.json if the Stage9 JSON patch was installed.
- Expected diagnostic log next to the proxy: Endurance2047.log with SOURCE_OK and HOOK_INSTALLED, otherwise GUARD_FAIL or HOOK_FAILED.
- No exe modification committed. User testing still required before declaring a successful cheat.

## Source
- cheats/endurance/dll/endurance2047_version.cpp
- cheats/endurance/dll/version_proxy.def
- cheats/endurance/dll/proxy_smoke.cpp
- cheats/endurance/dll/hook_smoke.cpp
- cheats/endurance/dll/README.md
- .github/workflows/endurance-dll-build.yml
