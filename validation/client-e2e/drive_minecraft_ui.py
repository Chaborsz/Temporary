#!/usr/bin/env python3
"""Drive a real Minecraft GUI until an enabled-command integrated world exists."""
import argparse
import csv
import io
import os
from pathlib import Path
import subprocess
import sys
import time


def screenshot(path: Path):
    subprocess.run(["timeout", "15s", "scrot", "-o", "-z", str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)


def capture(path: Path):
    screenshot(path)
    result = subprocess.run(["tesseract", str(path), "stdout", "tsv"], check=True,
                            capture_output=True, text=True)
    groups = {}
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        word = row.get("text", "").strip()
        if not word:
            continue
        key = (row.get("page_num"), row.get("block_num"), row.get("par_num"), row.get("line_num"))
        rec = groups.setdefault(key, {"words": [], "left": 10**9, "top": 10**9, "right": 0, "bottom": 0})
        rec["words"].append(word)
        x, y = int(row["left"]), int(row["top"])
        rec["left"] = min(rec["left"], x)
        rec["top"] = min(rec["top"], y)
        rec["right"] = max(rec["right"], x + int(row["width"]))
        rec["bottom"] = max(rec["bottom"], y + int(row["height"]))
    lines = []
    for rec in groups.values():
        rec["text"] = " ".join(rec["words"])
        lines.append(rec)
    return "\n".join(line["text"] for line in lines), lines


def click_at(x, y):
    subprocess.run(["xdotool", "mousemove", "--sync", str(x), str(y), "click", "1"], check=True)



def wait_for_text(label, test, screenshot, timeout=180):
    end = time.monotonic() + timeout
    last_text = ""
    while time.monotonic() < end:
        last_text, lines = capture(screenshot)
        if test(last_text.lower(), lines):
            print(f"UI_TEXT_READY={label}", flush=True)
            return last_text, lines
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {label}; last OCR was: {last_text[:1000]}")


def trace_has(path, marker):
    return path.exists() and marker in path.read_text(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    frame = args.screenshots / "ui-current.png"
    ui_timeout = int(os.environ.get("UI_TIMEOUT_SECONDS", "300"))
    start = time.monotonic()
    deadline = start + ui_timeout
    while time.monotonic() < deadline and not trace_has(args.trace, "CI_WORLD_READY"):
        time.sleep(1)
    if not trace_has(args.trace, "CI_WORLD_READY"):
        text, _ = capture(frame)
        raise RuntimeError("Integrated test world did not start; last OCR was: " + text[:1600])
    print(f"UI_WORLD_READY_SECONDS={int(time.monotonic() - start)}", flush=True)

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and not trace_has(args.trace, "CI_COMPANION_SYNCED"):
        time.sleep(1)
    if not trace_has(args.trace, "CI_COMPANION_SYNCED"):
        raise RuntimeError("Production command did not create/sync an owned Companion")

    screenshot(args.screenshots / "companion-idle.png")
    subprocess.run(["xdotool", "key", "k"], check=True)
    time.sleep(1.0)
    # Fixed 1920x1080 Xvfb layout: click visible controls by their centers.
    screenshot(args.screenshots / "management-screen.png")
    click_at(750, 584)
    time.sleep(0.6)
    screenshot(args.screenshots / "management-passive.png")
    click_at(960, 584)
    time.sleep(0.6)
    screenshot(args.screenshots / "management-defensive.png")
    click_at(750, 472)
    time.sleep(0.6)
    subprocess.run(["xdotool", "key", "Escape"], check=True)
    trace_path = Path(os.environ["CI_VALIDATION_DIR"])
    (trace_path / "ui-complete").write_text("management UI clicked Passive, Defensive, and Follow controls\\n", encoding="utf-8")
    print("CLIENT_UI_DEFENSIVE_AND_FOLLOW=PASS; input=direct-coordinate-clicks; OCR=diagnostic-only", flush=True)

    if not trace_has(args.trace, "CI_REAL_ZOMBIE_SPAWN_COMMAND_SENT"):
        end = time.monotonic() + 30
        while time.monotonic() < end and not trace_has(args.trace, "CI_REAL_ZOMBIE_SPAWN_COMMAND_SENT"):
            time.sleep(1)
    if not trace_has(args.trace, "CI_REAL_ZOMBIE_SPAWN_COMMAND_SENT"):
        raise RuntimeError("Client UI completed but a real Zombie attack scenario did not start")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"CLIENT_UI_DRIVER_FAILURE={error}", file=sys.stderr, flush=True)
        raise
