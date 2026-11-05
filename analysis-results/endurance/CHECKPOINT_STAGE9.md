# Endurance ID2047 freeze0 — STAGE9 experimental build

## Result
- CI run: https://github.com/Chaborsz/Temporary/actions/runs/41950823302
- Status: SUCCESS. Full Weakfish CBC decrypt->encrypt->decrypt roundtrip SHA check PASS.
- Artifact: https://github.com/Chaborsz/Temporary/actions/runs/41950823302/artifacts/13380957331
- Artifact name: Endurance-2047-freeze0-TEST-41950823302
- Artifact total size: 302,000,477 bytes.
- Inner game candidate: endurance_2047_freeze0_TEST.zip (301,997,150 bytes).
- Candidate ZIP contains one encrypted project.json, 301,997,028 bytes.
- Script: cheats/endurance/stage9_freeze_2047.py
- Installation and rollback: cheats/endurance/PRUEBA_FREEZE_2047.md

## Verified static changes
- Original plaintext game project: 301,997,021 bytes.
- Source SHA256: 2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89.
- 8,813 exact global variable ID2047 setters found.
- 16,070 same-length edits total:
  - 8,813 numeric assignValue replacements to zero;
  - 7,257 variableAssignOperator replacements to assignment (operator 0);
  - variableAssignValueType was already 0 at each matched setter; no replacements needed.
- 0 non-global setters modified.
- No changes to other variable identifiers, condition comparisons, scene definitions, object lists, game executable, HP or MP.
- All file edits are confined to assignment operator/value for global variable ID2047.
- Patches were applied to copy of canonical decoded source in CI; original Release asset and game source were NOT modified.
- Full project JSON streamed to verify global variable ID2047 remained defined and valid.
- Encrypted project.json produced with AGTK Weakfish CBC and verified by full decrypt SHA matching patched source.
- ZIP CRC/size check PASS.

## Limits
- This is a **reversible, untested runtime candidate**, not a proven cheat.
- Expected effect: force all recorded writes to temptation gauge ID2047 to assign zero.
- Side effects: scenes that require reaching 75/76 temptation may stop progressing; loaded saves may restore prior nonzero values until a setter executes.
- The exact English Endurance HUD label has not been correlated visually with UI object49.
- The game build on the user's machine must match the project release; check encrypted original project.json size exactly 301,997,028 bytes before swapping.
- Always back up original Resources/data/project.json and saves. Restore backup if the test is wrong.
- Workflow artifact expires after 7 days; no full modified game data has been committed to the public repository.

## Next
User runtime check: does the Endurance bar below HP/MP stay empty while exposed to temptation? Does play progress and other bars still behave normally? If confirmed, optimize patch scope and produce a stable candidate with appropriate regressions.
