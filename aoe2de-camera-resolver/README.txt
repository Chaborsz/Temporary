AOE2DE 101.103.54800.0 - CAMERA DISCRIMINATOR RC8

Purpose:
Find the real direct camera X/Y state by separating camera-pan changes from mouse-only changes. This build is read-only. It does not spawn units and does not write game memory.

Install:
1. Close AoE2DE.
2. Back up the current version.dll.
3. Put this diagnostic version.dll beside AoE2DE_s.exe.
4. Start AoE2DE and enter a live match.

IMPORTANT: keep zoom unchanged for all six samples.

Samples 1-3: camera movement
1. Put cursor near screen center. Camera position A. Press F11.
2. Pan camera far away WITHOUT changing zoom, recenter cursor, press F11.
3. Pan camera elsewhere WITHOUT changing zoom, recenter cursor, press F11.

Samples 4-6: mouse-only movement
4. Keep camera exactly fixed, cursor near center, press F11.
5. Keep camera fixed, move cursor to upper-left interior (not screen edge), press F11.
6. Keep camera fixed, move cursor to lower-right interior (not screen edge), press F11.

Each sample emits a beep. The sixth sample performs the correlation and may take about a second.

Return:
%TEMP%\AoE2DE_P3O_54800_CameraDiscriminator_RC8.txt

The report ranks adjacent float pairs that change during camera panning but remain stable during mouse-only movement.

After testing restore the prior spawner version.dll.
