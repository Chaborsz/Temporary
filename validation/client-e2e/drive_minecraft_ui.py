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
import shutil


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


def click_line(lines, includes, *, minimum_y=0, maximum_y=1080):
    wanted = includes.lower()
    candidates = [line for line in lines if wanted in line["text"].lower()
                  and minimum_y <= (line["top"] + line["bottom"]) // 2 <= maximum_y]
    if not candidates:
        return False
    line = candidates[-1]
    subprocess.run(["xdotool", "mousemove", str((line["left"] + line["right"]) // 2),
                    str((line["top"] + line["bottom"]) // 2), "click", "1"], check=True)
    return True


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
    end = start + ui_timeout
    last_report = start
    commands_enabled = False

    while time.monotonic() < end and not trace_has(args.trace, "CI_WORLD_READY"):
        text, lines = capture(frame)
        low = text.lower()
        now = time.monotonic()
        if now - last_report >= 10:
            elapsed = int(now - start)
            snapshot = args.screenshots / f"ui-progress-{elapsed:04d}.png"
            shutil.copy2(frame, snapshot)
            print(f"UI_PROGRESS_SECONDS={elapsed} OCR={text[:700]!r}", flush=True)
            last_report = now
        if "welcome to minecraft" in low and click_line(lines, "continue"):
            print("UI_CLICK=accessibility_continue", flush=True)
        elif "singleplayer" in low and click_line(lines, "singleplayer"):
            print("UI_CLICK=singleplayer", flush=True)
        elif "game mode" in low and ("allow commands" in low or "allow cheats" in low):
            if ("allow commands on" in low or "allow commands: on" in low
                    or "allow cheats on" in low or "allow cheats: on" in low):
                commands_enabled = True
            if "allow commands off" in low or "allow cheats off" in low or "allow commands: off" in low:
                click_line(lines, "allow commands") or click_line(lines, "allow cheats")
                print("UI_CLICK=enable_commands", flush=True)
                time.sleep(1)
                continue
            if commands_enabled and click_line(lines, "create new world", minimum_y=600):
                print("UI_CLICK=create_world_start", flush=True)
        elif "create new world" in low:
            if click_line(lines, "create new world", minimum_y=600):
                print("UI_CLICK=create_world_select", flush=True)
        elif "select world" in low and click_line(lines, "create new world", minimum_y=600):
            print("UI_CLICK=create_world_select", flush=True)
        time.sleep(2)

    if not trace_has(args.trace, "CI_WORLD_READY"):
        raise RuntimeError("Integrated world did not reach the real client harness; last OCR was: " + text[:1600])

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and not trace_has(args.trace, "CI_COMPANION_SYNCED"):
        time.sleep(1)
    if not trace_has(args.trace, "CI_COMPANION_SYNCED"):
        raise RuntimeError("Production command did not create/sync an owned Companion")

    screenshot(args.screenshots / "companion-idle.png")
    subprocess.run(["xdotool", "key", "k"], check=True)
    mode_text, mode_lines = wait_for_text(
        "Companion management screen with Defensive mode",
        lambda text, lines: "companion" in text and "combat" in text and "defensive" in text,
        args.screenshots / "management-current.png", timeout=90)
    (args.screenshots / "management-screen-ocr.txt").write_text(mode_text, encoding="utf-8")
    screenshot(args.screenshots / "management-defensive.png")

    if not click_line(mode_lines, "defensive mode"):
        if not click_line(mode_lines, "defensivo"):
            raise RuntimeError("The real management UI did not expose its Defensive mode control")
    time.sleep(1)
    text, lines = capture(args.screenshots / "management-current.png")
    if not click_line(lines, "follow") and not click_line(lines, "seguir"):
        raise RuntimeError("The real management UI did not expose its Follow order control")
    time.sleep(1)
    subprocess.run(["xdotool", "key", "Escape"], check=True)
    trace_path = Path(os.environ["CI_VALIDATION_DIR"])
    (trace_path / "ui-complete").write_text("management UI selected Defensive + Follow\n", encoding="utf-8")
    print("CLIENT_UI_DEFENSIVE_AND_FOLLOW=PASS", flush=True)

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
