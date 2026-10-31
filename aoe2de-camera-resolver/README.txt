AOE2DE 101.103.54800.0 - P3O OVERLAY + POINT-AT-MOUSE RC9 FIX2

Runtime candidate, not Stable.

FIX2 specifically addresses FIX1 showing neither overlay nor spawn.
The fatal PE identity gate and fatal world-context gate have been removed from bootstrap. The DLL now binds to the real foreground AoE2DE window by process + client size, while world state is logged only for diagnosis/lifecycle. F12 is no longer blocked by world_probe.

Preserved:
- no-activate selector overlay;
- F12 spawn on subclassed game WndProc;
- Ctrl+F12 / Shift+F12 selection;
- 13-position collision fallback;
- direct 54800 camera X/Y 0x04416E40/0x04416E44;
- zoom 0x040957D8;
- xsCreateUnit 0x01812E50;
- existing AoE2DE_P3N.ini / AoE2DE_P3O.ini is reused and never overwritten.

Install version.dll beside AoE2DE_s.exe with your current INI unchanged.

First runtime test:
1. Enter a live match.
2. Confirm the selector overlay appears.
3. Press F12 once near screen center.
4. If that works, test opposite screen quadrants and another zoom level.
5. Close naturally.

Runtime log:
%TEMP%\AoE2DE_P3O_54800_RC9_FIX2.log
