#!/usr/bin/env python3
"""Capture real rendered attack frames and HUD states from the running client."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def screenshot(path: Path):
    subprocess.run(["timeout", "15s", "scrot", "-o", "-z", str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)


def wait_marker(trace: Path, marker: str, timeout=60):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if trace.exists() and marker in trace.read_text(encoding="utf-8", errors="replace"):
            return True
        time.sleep(0.25)
    return False


def send_chat(command: str):
    subprocess.run(["xdotool", "key", "t"], check=True)
    time.sleep(0.3)
    subprocess.run(["xdotool", "type", "--clearmodifiers", command if command.startswith("/") else "/" + command], check=True)
    subprocess.run(["xdotool", "key", "Return"], check=True)
    time.sleep(1.0)


def watch_attacks(trace: Path, output: Path):
    seen = 0
    stage = 0
    stage_start = time.monotonic()
    deadline = time.monotonic() + int(os.environ.get("CLIENT_TIMEOUT_SECONDS", "900"))
    while time.monotonic() < deadline:
        text = trace.read_text(encoding="utf-8", errors="replace") if trace.exists() else ""
        hits = [line for line in text.splitlines() if "CI_COMPANION_DAMAGE" in line]
        if len(hits) > seen:
            for attack_index, line in enumerate(hits[seen:], seen + 1):
                (output / f"attack-event-{attack_index}.txt").write_text(line + "\n", encoding="utf-8")
                style = "sword" if "weapon=minecraft:iron_sword" in line else "empty-hand"
                # Capture the active entity render repeatedly at a dense cadence.
                # The exact vanilla swing phase is animation-progress driven, so
                # preserve the full temporal sequence for visual frame inspection.
                for frame in range(24):
                    screenshot(output / f"swing-{style}-{attack_index}-frame-{frame:02d}.png")
                    time.sleep(0.025)
            seen = len(hits)
        if "CI_OWNER_DEFENSE_E2E_FAIL" in text:
            return 1
        if stage == 0 and "CI_OWNER_DEFENSE_E2E_PASS" in text:
            # The owner-defense chain is complete. Prove render swings with
            # autonomous production combat, independent of how many E2E hits
            # the earlier scanner happened to observe.
            send_chat("gamemode creative")
            send_chat("time set noon")
            send_chat("effect give @p minecraft:night_vision 120 0 true")
            send_chat("companion order follow")
            send_chat("tp @e[type=minecraft_companion:companion,limit=1,sort=nearest] @p")
            send_chat("companion mode aggressive")
            # Keep the Companion alive for multiple visible matrix cases; this
            # is a validation-only survival effect, not a combat-state mutation.
            send_chat("effect give @e[type=minecraft_companion:companion,limit=1,sort=nearest] minecraft:resistance 120 255 true")
            send_chat("companion appearance model default")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] weapon.mainhand with minecraft:air")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] armor.chest with minecraft:iron_chestplate")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] armor.head with minecraft:iron_helmet")
            send_chat("summon minecraft:zombie ~-5 ~ ~ {PersistenceRequired:1b,Health:40.0f}")
            stage = 1
            stage_start = time.monotonic()
        default_empty = [line for line in hits if "model=DEFAULT" in line and "weapon=minecraft:air" in line]
        sword_hits = [line for line in hits if "weapon=minecraft:iron_sword" in line]
        if stage == 1 and default_empty:
            send_chat("companion appearance model default")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] weapon.mainhand with minecraft:iron_sword")
            send_chat("summon minecraft:zombie ~-5 ~ ~ {PersistenceRequired:1b,Health:40.0f}")
            stage = 2
            stage_start = time.monotonic()
        if stage == 2 and len(sword_hits) >= 2:
            # Slim model with sleeves/base layer, held item and armor; an
            # intentional walk order gives the renderer a walk+attack case.
            send_chat("companion order follow")
            send_chat("companion appearance model slim_arms")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] weapon.mainhand with minecraft:iron_sword")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] armor.chest with minecraft:iron_chestplate")
            send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] armor.head with minecraft:iron_helmet")
            send_chat("tp @e[type=minecraft_companion:companion,limit=1,sort=nearest] @p ~4 ~ ~")
            send_chat("summon minecraft:zombie ~-5 ~ ~ {PersistenceRequired:1b,Health:40.0f}")
            stage = 3
            stage_start = time.monotonic()
        slim_sword = [line for line in hits if "model=SLIM_ARMS" in line and "weapon=minecraft:iron_sword" in line]
        if stage == 3 and len(slim_sword) >= 2:
            (output / "swing-visual-matrix.txt").write_text(
                "Classic/default + empty hand + chestplate + helmet: real rendered frames during production melee.\n"
                "Classic/default + iron sword + chestplate + helmet: real rendered frames during production melee.\n"
                "Slim arms + iron sword + chestplate + helmet + follow movement: real rendered frames during production melee.\n"
                "Each attack-event has 24 consecutive client screenshots; inspect temporal phases and returning idle pose visually.\n"
                "All attack screenshots are rendered frames associated with actual companion-attributed Zombie health loss.\n"
                "Sleeve appearance is whatever the configured production skin layer renders; separate layer visibility is not asserted by pixel inspection in this harness.\n",
                encoding="utf-8")
            return 0
        if stage and time.monotonic() - stage_start > 180:
            (output / "swing-visual-matrix-failure.txt").write_text(
                f"Timed out in stage {stage}; defaultEmptyHits={len(default_empty)}; swordHits={len(sword_hits)}; slimEmptyHits={len(slim_empty)}\n{text[-6000:]}",
                encoding="utf-8")
            return 1
        time.sleep(0.05)
    return 2


def hud_screens(trace: Path, output: Path):
    # Owner-defense already proved real damage, acquisition, pursuit and melee
    # response. Use that same live client session for the HUD captures.
    states = (("full", "health=24.0 food=20"), ("partial", "health=23.0 food=19"),
              ("empty", "health=12.0 food=10"), ("critical", "health=1.0 food=1"))
    send_chat("companion mode passive")
    send_chat("companion order follow")
    send_chat("tp @e[type=minecraft_companion:companion,limit=1,sort=nearest] @p")
    send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] armor.head with minecraft:iron_helmet")
    for name, marker in states:
        send_chat(f"cihud {name}")
        if not wait_marker(trace, f"CI_HUD_STATE {marker}", timeout=20):
            raise RuntimeError(f"the integrated server did not acknowledge HUD state {name}")
        time.sleep(0.5)
        screenshot(output / f"hud-{name}.png")
    (output / "hud-states.txt").write_text(
        "Captured with the real Fabric client after the validation-only command set Companion health/food.\n"
        "full=24/20; partial=23/19; empty=12/10; critical=1/1; iron helmet equipped for clearance view.\n",
        encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.watch:
        raise SystemExit(watch_attacks(args.trace, args.output))
    if not wait_marker(args.trace, "CI_OWNER_DEFENSE_E2E_PASS", timeout=3):
        raise RuntimeError("owner-defense pass marker is absent")
    screenshot(args.output / "owner-defense-after-response.png")
    hud_screens(args.trace, args.output)
    print("REAL_CLIENT_SCREENSHOTS=CAPTURED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"CLIENT_EVIDENCE_FAILURE={error}", file=sys.stderr, flush=True)
        raise
