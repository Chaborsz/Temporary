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
    subprocess.run(["xdotool", "type", "--clearmodifiers", command], check=True)
    subprocess.run(["xdotool", "key", "Return"], check=True)
    time.sleep(1.0)


def watch_attacks(trace: Path, output: Path):
    seen = 0
    deadline = time.monotonic() + int(os.environ.get("CLIENT_TIMEOUT_SECONDS", "900"))
    while time.monotonic() < deadline:
        text = trace.read_text(encoding="utf-8", errors="replace") if trace.exists() else ""
        hits = [line for line in text.splitlines() if "CI_COMPANION_DAMAGE" in line]
        if len(hits) > seen:
            for attack_index, line in enumerate(hits[seen:], seen + 1):
                (output / f"attack-event-{attack_index}.txt").write_text(line + "\n", encoding="utf-8")
                style = "sword" if "weapon=minecraft:iron_sword" in line else "empty-hand"
                for frame in range(8):
                    screenshot(output / f"swing-{style}-{attack_index}-frame-{frame:02d}.png")
                    time.sleep(0.045)
            seen = len(hits)
        if "CI_OWNER_DEFENSE_E2E_FAIL" in text:
            return 1
        if "CI_OWNER_DEFENSE_E2E_PASS" in text and any(
                "weapon=minecraft:iron_sword" in line for line in hits):
            return 0
        time.sleep(0.05)
    return 2


def hud_screens(trace: Path, output: Path):
    send_chat("item replace entity @e[type=minecraft_companion:companion,limit=1,sort=nearest] weapon.mainhand with minecraft:iron_sword")
    # The owner-defense scenario has already passed. Switch through the public
    # owner command to test a real, visible sword attack without synthetic targets.
    send_chat("companion mode aggressive")
    send_chat("summon minecraft:zombie ~-3 ~ ~ {PersistenceRequired:1b}")
    if not wait_marker(trace, "weapon=minecraft:iron_sword", timeout=120):
        raise RuntimeError("a real sword attack did not produce a Companion melee damage event")
    time.sleep(0.5)
    screenshot(output / "sword-attack-after-response.png")
    states = (("full", "health=24.0 food=20"), ("partial", "health=23.0 food=19"),
              ("empty", "health=12.0 food=10"), ("critical", "health=1.0 food=1"))
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
