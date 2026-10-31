AOE2DE 101.103.54800.0 - CAMERA CANDIDATE RC7

Purpose:
Confirm whether the direct floats at RVA 0x04416E40 / 0x04416E44 are the camera center, while keeping zoom at confirmed RVA 0x040957D8.
This build is read-only. It does not spawn units and does not write game memory.

Install:
1. Close AoE2DE.
2. Back up the current version.dll.
3. Put this diagnostic version.dll beside AoE2DE_s.exe.
4. Start AoE2DE and enter a live match.

Capture protocol — IMPORTANT:
Keep the CAMERA and ZOOM completely fixed for all three samples. Move ONLY the mouse cursor.

1. Put mouse near the center of the game view -> F11.
2. Without moving/zooming the camera, put mouse near the upper-left of the game view -> F11.
3. Without moving/zooming the camera, put mouse near the lower-right of the game view -> F11.

Each successful sample emits a Windows beep.
Return this file:
%TEMP%\AoE2DE_P3O_54800_CameraCandidate_RC7.txt

Expected confirmation:
- camera=(X,Y) must remain effectively identical in all 3 samples.
- zoom must remain identical.
- mouse and projected target must change.

After testing restore the prior spawner version.dll.
