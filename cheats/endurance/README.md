# AGTK Endurance / excitation — external static audit

## Canonical input
- Original: ChatGPT Library /player.exe (not hosted here)
- PE32 x86, base 0x00400000, 8,757,760 bytes.
- Required SHA-256: 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea
- Engine: AGTK / Pixel Game Maker MV (Cocos2d-x).
- Original archive of earlier static candidates: ChatGPT Library /player_cheats_auditoria.zip.
- The existing earlier report has a typo for getHp RVA. This target EXCLUDES HP entirely.

## Current target
Endurance = aguante/excitación, displayed below HP and MP. Determine its actual data variable, readers, writers, consumption and regeneration, and whether modifying them would affect the player alone. Do not equate Endurance with HP, MP, or a generic engine value without evidence.

## Current state
- No verified live Endurance address or function.
- No tested cheat, runtime validation or edited game binary.
- This workflow does not create a cheat or patch; it records static evidence.
- The program checks source identity and emits a compact JSON checkpoint.
- **The canonical EXE/ZIP from ChatGPT Library cannot currently be copied to GitHub by the connected tools.** No input has been uploaded. Do not interpret SOURCE_REQUIRED as a failed disassembly.

## Inputs expected by Actions
- cheats/endurance/input/player.exe (the original unmodified executable, byte-for-byte)
- Optionally place game project text assets (JSON, CSV, DAT, etc.) in cheats/endurance/input/game-data/.
- Optionally place the earlier player_cheats_auditoria.zip under cheats/endurance/input/ for reference.

The **repository is public**. Uploading the EXE or game assets here makes them publicly accessible in repository history. Only upload files you are authorized to redistribute. A private repository or an authenticated file-transfer route is preferable for copyrighted game content.

## Outputs
- Actions workflow: .github/workflows/endurance-audit.yml
- Script: cheats/endurance/analyze_endurance.py
- Run artifact: endurance-audit-RUN_ID, containing CHECKPOINT.md and endurance-audit.json
- Status SOURCE_REQUIRED: absent original input
- Status SOURCE_MISMATCH: byte size or SHA mismatch; no analysis of wrong binary
- Status AUDITED_NO_DIRECT_TERM: no direct name evidence; requires game-data/dynamic correlation
- Status AUDITED_WITH_DIRECT_TERMS: candidate strings found, NOT yet verified as live variable

No changes to other Temporary projects.
