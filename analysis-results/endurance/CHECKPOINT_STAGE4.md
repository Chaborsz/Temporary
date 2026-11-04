# Endurance / Weakfish STAGE4 checkpoint — 2026-11-04

SOURCE: Forest of the Blue Skin Build 29 (Pixel Game Maker MV / AGTK)
FOCUS: Endurance = aguante/excitación HUD below HP/MP; HP EXCLUDED.

## Recovered valid previous state
- Previous Windows script: decrypt_fobs_build29.ps1.
- Input: Resources\\data\\project.json.
- Key in Resources\\data\\info.json: bytes "232301 " (trailing space), len=7.
- Legacy cipher: Weakfish-CBC, header 'enc' + padding count (previous: 0x02), 16-byte ciphertext blocks.
- Previous decoded project_decrypted.json size: 294,287,854 bytes. JSON validity confirmed previously.
- This is an earlier confirmed result, not a new actual decryption run.

## New implementation
- cheats/endurance/decode_project_weakfish.py: streaming weakfish-CBC decoder + ijson Endurance variable/metadata search, does not persist or upload full 294MB plaintext.
- .github/workflows/endurance-audit.yml: supports optional release asset named exactly project.json, auto-trigger on published release or manual workflow_dispatch input release_tag.
- End-to-end synthetic encrypted-file CBC + JSON scanner validation: PASS.
- GitHub Actions validated: https://github.com/Chaborsz/Temporary/actions/runs/41927014374 (SUCCESS)
- Current stage 4: SOURCE_MISSING. Neither encrypted project.json nor earlier project_decrypted.json is in the repository, so there is no newly decoded real JSON or identified Endurance ID.

## Next
- Supply the previously decrypted project_decrypted.json (if still available) via a secure route, OR attach original Resources\\data\\project.json as Release asset in an authorized repository (not a normal commit; input size exceeds ordinary GitHub limits).
- Repo Chaborsz/Temporary is PUBLIC: any Release asset is public and may expose copyrighted game data. Prefer a private repo or local extraction of the small stage4 report when redistribution is not authorized.
- Then run stage 4 on real game-data, correlate Endurance with numeric variable/object ID and trace gauge read/write paths. No patch or cheat has been created.
