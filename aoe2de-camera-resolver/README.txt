AOE2DE 101.103.54800.0 - INTERNAL CAMERA RESOLVER RC6

Purpose:
Resolve the Point-at-Mouse camera global and zoom RVA from inside AoE2DE_s.exe.
RC6 scans the whole mutable/data tail of the module instead of a narrow window around the old candidates.
This diagnostic does not spawn units and does not write game memory.

Install:
1. Close the game.
2. Back up the current version.dll used by the spawner.
3. Put this diagnostic version.dll beside AoE2DE_s.exe.
4. Start the game and enter a live match.

Capture:
1. Leave the camera at position A and a normal zoom. Press F11 once.
2. Pan the camera far away and zoom strongly in. Press F11 once.
3. Pan to another area and zoom strongly out. Press F11 once.

Each successful sample emits a Windows beep. The first sample can take longer because RC6 scans the full data range.
After the third sample, collect:
%TEMP%\AoE2DE_P3O_54800_InternalCameraResolver_RC6.txt

Return that TXT to ChatGPT.

After testing, restore the prior spawner version.dll.
