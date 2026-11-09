# ShironoYakata DEMO — Native multi-clone TEST v0.1

Only for exact original demo binary:

- player.exe SHA-256: d91263d4245e029dc0942c1f66bfde712dbc7aeb940737fc3515e48f4f0eb154
- project_decrypted.json SHA-256: 197f001d7d0d8d4b685a3f9f7a720c5c51055240e8f16cfd1d65062ed0578d57
- Source bundle: ShironoYakata-DEMO/project_decrypted.7z

## Behavior

The game uses AGTK Object ID 1 for player and native clone Object ID 19 (分身プレイヤー).
On the game's existing clone-summon action, the DLL calls the original
agtk::Object::execActionObjectCreate once and then twice more by default,
reusing native action, connection, direction, and instance-allocation logic.

player.exe imports VERSION.dll (3 functions). The x86 proxy forwards ten version-library
functions to the real Windows version.dll and patches agtk::Object::execActionObjectCreate
at RVA 0x001284A0. Both full EXE SHA-256 and original 5-byte entry signature are verified.

## Install / configuration

Put dist/version.dll next to the actual installed game's player.exe.
Back up any existing version.dll.

Optionally create ShironoMulticlone.ini with the following two lines:

    [ShironoMulticlone]
    ExtraClones=2

ExtraClones is 0..6. With 2 the normal in-game summon attempts to spawn 3 clones
including the original. The game determines when to summon; no new hotkey is needed.
The setting is read at process launch.

ShironoMulticlone.log in the game's folder records EXE_SHA256_MATCH and HOOK_READY.
When a clone command is intercepted it writes NATIVE_CLONE_COMMAND id=19 copies=3.

## Scope / caveats

- Experimental: runtime not tested, no complete installed game or graphics assets in CI.
- Native game events may remove duplicate clones after creation; game behavior must be tested.
- Windows 32-bit, exact SHA only; wrong EXE disables hook but VERSION forwarding stays active.
- Only object ID 19 is multiplied; no changes to EXE or JSON, camera or original player.
- To uninstall, remove the proxy DLL and its optional ini/log.

## Evidence

- https://github.com/Chaborsz/Ghidra-12.1.4-Workspace/tree/analysis/shirono-multiclone/audit-out/shirono
- https://github.com/Chaborsz/Ghidra-12.1.4-Workspace/tree/analysis/shirono-multiclone/audit-out/shirono-stage2

Native Object::execActionObjectCreate: VA 0x005284A0, RVA 0x001284A0.
Original native code assigns separate instance IDs and instance counts, and inserts
objects into a SceneLayer. Player object 1 summons clone object 19 in actions 118
and 135 with connection 6.

## Build

GitHub Actions Windows MSVC x86 workflow: .github/workflows/shirono-native-multiclone.yml
Output: dist/version.dll (x86).
