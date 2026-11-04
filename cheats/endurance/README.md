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

## Build 29 encrypted project.json (stage 4)
Previous verified local Windows decryption (2026-10-18):
- Input: `Resources\data\project.json`
- `Resources\data\info.json` key resolves to seven bytes `232301 ` (**trailing space is significant**).
- Encryption: legacy Weakfish CBC, header `enc\\x02` and 16-byte blocks; do **not** use modern Twofish.
- Earlier output `project_decrypted.json` was **294,287,854 bytes** and valid JSON.
- Earlier local script: `decrypt_fobs_build29.ps1`; if its original output is still available, it may be reused rather than decrypted again.

Stage-4 source and workflow:
- `cheats/endurance/decode_project_weakfish.py` is a streaming Python reimplementation of the MIT-licensed PGMM Weakfish logic, with a roundtrip self-test.
- No full 294 MB decoded copy is committed or archived; the temporary decoded JSON is deleted after streaming `ijson` scanning. Only a bounded Endurance metadata report is retained.
- `on: release/published` or manual `workflow_dispatch` with `release_tag`: downloads an asset **named exactly `project.json`** from that GitHub Release and processes it.
- A plain already-decoded `cheats/endurance/input/project_decrypted.json` also works, if supplied through an appropriate authorized input channel.
- If no project source is available, the workflow self-test runs and records `SOURCE_MISSING`; this is not a decryption failure.

### Large-file transfer (only if you are authorized to redistribute the file)
GitHub normal repository uploads are unsuitable for this ~294 MB encrypted file. Use Releases:
1. In `Chaborsz/Temporary`, open **Releases -> Draft a new release**.
2. Choose an unused tag, e.g. `fobs-build29-endurance-input`.
3. Attach the encrypted **`Resources\data\project.json`** as a release asset named `project.json`.
4. Publish the release only after the asset is attached. GitHub Actions should run stage 4 automatically.
5. Alternatively use the workflow's manual `release_tag` input to process an existing release.

**IMPORTANT: the current repository is PUBLIC. Release assets become public too.** A private repository or processing locally and uploading only a small extracted report is safer for proprietary game data. Do not upload the entire decrypted project publicly.

Source for the historic Weakfish algorithm: https://github.com/blluv/pgmm_decrypt (MIT).
