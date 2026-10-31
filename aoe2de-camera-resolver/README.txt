AOE2DE 101.103.54800.0 - P3O OVERLAY + POINT-AT-MOUSE RC9 FIX1

This replaces the incorrect resolver-based RC9. It is a runtime candidate, not Stable.

Restored behavior:
- ownerless/no-activate in-game selector overlay;
- overlay hidden outside a live match or when AoE2DE loses foreground;
- F12 spawn on the game WndProc/main UI thread;
- Ctrl+F12 next unit, Shift+F12 previous unit;
- 13-position collision fallback;
- Point-at-Mouse using the 54800 runtime-proven camera and zoom state.

54800 mappings:
Camera X = 0x04416E40
Camera Y = 0x04416E44
Zoom = 0x040957D8
World = 0x04353698
xsCreateUnit = 0x01812E50

INI:
The DLL does not install or overwrite an INI. It first reads AoE2DE_P3N.ini beside AoE2DE_s.exe, then AoE2DE_P3O.ini if present. A named unit_cycle such as 83:Villager|74:Militia is supported, as is a comma-separated numeric cycle. If no readable cycle exists, the eight Viking Sagas heroes are used as the fallback catalog.

Install:
1. Close AoE2DE.
2. Back up the current version.dll.
3. Keep the existing P3N/P3O INI in place.
4. Put version.dll beside AoE2DE_s.exe.
5. Start a live match.

Test:
- overlay appears in the match and disappears in menus/Alt-Tab;
- select a unit from the overlay;
- press F12 near screen center and in opposite quadrants;
- repeat at more than one zoom level;
- Ctrl+F12 / Shift+F12 change selection;
- close the game naturally.

Runtime log:
%TEMP%\AoE2DE_P3O_54800_RC9_FIX1.log

Return the runtime result/log after testing.
