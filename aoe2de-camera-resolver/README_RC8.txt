AoE2DE 101.103.54800.0 CAMERA DISCRIMINATOR RC8

Purpose: identify the real direct camera X/Y state by separating camera-pan changes from mouse-only changes. Read-only self-process diagnostic.

Protocol (keep zoom unchanged for all six samples):
1. Put cursor near screen center. Camera position A. Press F11.
2. Pan camera far away WITHOUT changing zoom, recenter cursor, press F11.
3. Pan camera elsewhere WITHOUT changing zoom, recenter cursor, press F11.
4. Keep camera exactly fixed, cursor near center, press F11.
5. Keep camera fixed, move cursor to upper-left interior (not screen edge), press F11.
6. Keep camera fixed, move cursor to lower-right interior (not screen edge), press F11.

Each sample beeps. Return %TEMP%\AoE2DE_P3O_54800_CameraDiscriminator_RC8.txt.
