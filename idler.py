#!/usr/bin/env python3
"""keyidler — idle game powered by your real keypresses across every app"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread

DATA_DIR  = Path.home() / ".keyidler"
DATA_FILE = DATA_DIR / "data.json"
PID_FILE  = DATA_DIR / "daemon.pid"

LEVELS = [
    (0,           "Sleeping Fingers"),
    (500,         "One-Finger Typist"),
    (2_000,       "Hunt & Pecker"),
    (5_000,       "The Noob"),
    (7_500,       "Warming Up"),
    (15_000,      "Average Clacker"),
    (25_000,      "Getting Serious"),
    (40_000,      "Keyboard Regular"),
    (80_000,      "Speed Demon"),
    (120_000,     "Key Addict"),
    (150_000,     "Keyboard Warrior"),
    (225_000,     "Iron Fingers"),
    (300_000,     "The Clackmaster"),
    (450_000,     "Veteran Clacker"),
    (600_000,     "Keyboard God"),
    (1_000_000,   "Transcendent Being"),
    (1_500_000,   "Legendary Typist"),
    (2_500_000,   "Mythical Keymaster"),
    (5_000_000,   "Digital Deity"),
    (10_000_000,  "The Infinite"),
    (25_000_000,  "Beyond Mortal"),
]

WORD_LEVELS = [
    (0,          "Silent"),
    (100,        "First Words"),
    (500,        "Sentence Maker"),
    (1_000,      "Paragraph Writer"),
    (2_500,      "Casual Conversant"),
    (5_000,      "Essay Crafter"),
    (10_000,     "Story Teller"),
    (25_000,     "Novelist in Training"),
    (50_000,     "The Wordsmith"),
    (100_000,    "Prolific Writer"),
    (250_000,    "Word Machine"),
    (500_000,    "Literary Legend"),
    (1_000_000,  "The Infinite Author"),
    (2_000_000,  "Word God"),
    (5_000_000,  "Transcendent Scribe"),
]

ACHIEVEMENTS = [
    ("first_100",   "Baby Steps",       "100 total keys"),
    ("first_1k",    "Kilokeys",         "1,000 total keys"),
    ("ten_k",       "Ten Thousand",     "10,000 total keys"),
    ("hundred_k",   "The Centurion",    "100,000 total keys"),
    ("mil",         "Million Keys",     "1,000,000 total keys"),
    ("night_owl",   "Night Owl",        "typed past midnight"),
    ("early_bird",  "Early Bird",       "typed before 6am"),
    ("marathon",    "Marathon",         "1,000 keys in one day"),
    ("century_day", "Century Day",      "10,000 keys in one day"),
    ("week",        "Week Warrior",     "typed on 7 different days"),
    ("month",       "Monthly Regular",  "typed on 30 different days"),
]

# (id, name, display_desc, cost_pts, ppt_bonus)
UPGRADES = [
    ("boost_1", "Nimble Fingers",   "+1 pt/key",   100,      1),
    ("boost_2", "Touch Typist",     "+2 pt/key",   400,      2),
    ("boost_3", "Speed Freak",      "+5 pt/key",   1_500,    5),
    ("boost_4", "Keyboard Wizard",  "+10 pt/key",  6_000,   10),
    ("boost_5", "Type God",         "+25 pt/key",  25_000,  25),
    ("boost_6", "Transcendent",     "+50 pt/key",  100_000, 50),
]


# ── data ──────────────────────────────────────────────────────────────────────

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "total": 0,
        "daily": {},
        "hours_active": [],
        "unlocked": [],
        "points_balance": 0,
        "upgrades_owned": [],
        "total_words": 0,
    }


def save_data(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(DATA_FILE)


def compute_ppt(data):
    owned = set(data.get("upgrades_owned", []))
    return 1 + sum(bonus for uid, _, __, ___, bonus in UPGRADES if uid in owned)


def get_level_idx(total, levels=None):
    if levels is None:
        levels = LEVELS
    idx = 0
    for i, (threshold, _) in enumerate(levels):
        if total >= threshold:
            idx = i
    return idx


def check_achievements(data):
    unlocked = set(data.get("unlocked", []))
    total    = data["total"]
    daily    = data.get("daily", {})
    hours    = set(data.get("hours_active", []))
    checks = {
        "first_100":   total >= 100,
        "first_1k":    total >= 1_000,
        "ten_k":       total >= 10_000,
        "hundred_k":   total >= 100_000,
        "mil":         total >= 1_000_000,
        "night_owl":   any(0 <= h <= 3 for h in hours),
        "early_bird":  any(4 <= h <= 5 for h in hours),
        "marathon":    any(v >= 1_000 for v in daily.values()),
        "century_day": any(v >= 10_000 for v in daily.values()),
        "week":        len(daily) >= 7,
        "month":       len(daily) >= 30,
    }
    for key, condition in checks.items():
        if condition and key not in unlocked:
            unlocked.add(key)
    data["unlocked"] = list(unlocked)


# ── daemon ────────────────────────────────────────────────────────────────────

_lock             = Lock()
_buffer           = 0
_words_buffer     = 0
_in_word          = False   # True when at least one non-delimiter key pressed since last delimiter
_running          = True

WORD_BONUS = 10  # pts awarded per completed word


def _flush():
    global _buffer, _words_buffer
    if _buffer == 0:
        return
    data  = load_data()
    today = datetime.now().strftime("%Y-%m-%d")
    hour  = datetime.now().hour
    ppt   = compute_ppt(data)
    earned = _buffer * ppt + _words_buffer * WORD_BONUS
    data["total"] += _buffer
    data["daily"][today] = data["daily"].get(today, 0) + _buffer
    hours = set(data.get("hours_active", []))
    hours.add(hour)
    data["hours_active"]   = sorted(hours)
    data["points_balance"] = data.get("points_balance", 0) + earned
    data["total_words"]    = data.get("total_words", 0) + _words_buffer
    check_achievements(data)
    save_data(data)
    _buffer = 0
    _words_buffer = 0


def _flush_loop():
    global _running
    while _running:
        time.sleep(5)
        with _lock:
            _flush()


def run_daemon():
    global _buffer, _running
    try:
        from pynput import keyboard
    except ImportError:
        sys.stderr.write("pynput not installed. Run: pip install pynput rich\n")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    Thread(target=_flush_loop, daemon=True).start()

    _DELIMITERS = {
        keyboard.Key.space, keyboard.Key.enter,
        keyboard.Key.tab,   keyboard.Key.backspace,
    }

    def on_press(key):
        global _buffer, _words_buffer, _in_word
        with _lock:
            _buffer += 1
            if key in _DELIMITERS:
                if key != keyboard.Key.backspace and _in_word:
                    _words_buffer += 1
                _in_word = False
            else:
                _in_word = True

    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    finally:
        _running = False
        with _lock:
            _flush()
        try:
            PID_FILE.unlink()
        except OSError:
            pass


# ── helpers ───────────────────────────────────────────────────────────────────

def is_daemon_running():
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True, pid
    except (ValueError, OSError):
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        return False, None


def require_rich():
    try:
        import rich  # noqa: F401
    except ImportError:
        print("rich not installed. Run: pip install pynput rich")
        sys.exit(1)


def try_buy_upgrade(uid):
    """Returns (success, message)."""
    upgrade_ids = [u[0] for u in UPGRADES]
    if uid not in upgrade_ids:
        return False, "Unknown upgrade."
    idx = upgrade_ids.index(uid)
    _, name, _, cost, _ = UPGRADES[idx]

    data  = load_data()
    owned = set(data.get("upgrades_owned", []))

    if uid in owned:
        return False, f"{name} already owned."
    if idx > 0 and upgrade_ids[idx - 1] not in owned:
        return False, f"Buy {UPGRADES[idx-1][1]} first."

    balance = data.get("points_balance", 0)
    if balance < cost:
        return False, f"Need {cost:,} pts  (have {balance:,})"

    data["points_balance"] = balance - cost
    owned.add(uid)
    data["upgrades_owned"] = list(owned)
    save_data(data)
    return True, f"Bought {name}!  Now earning {compute_ppt(data)} pt/key"


# ── display ───────────────────────────────────────────────────────────────────

def build_panel(message=None):
    from rich.panel   import Panel
    from rich.table   import Table
    from rich.text    import Text
    from rich.console import Group
    from rich         import box

    data        = load_data()
    total       = data["total"]
    daily       = data.get("daily", {})
    unlocked    = set(data.get("unlocked", []))
    balance     = data.get("points_balance", 0)
    total_words = data.get("total_words", 0)
    ppt         = compute_ppt(data)
    owned       = set(data.get("upgrades_owned", []))
    upgrade_ids = [u[0] for u in UPGRADES]

    lvl_idx  = get_level_idx(total)
    lvl_name = LEVELS[lvl_idx][1]
    if lvl_idx + 1 < len(LEVELS):
        nxt_thresh, nxt_name = LEVELS[lvl_idx + 1]
        cur_thresh           = LEVELS[lvl_idx][0]
        progress             = (total - cur_thresh) / (nxt_thresh - cur_thresh)
        keys_left            = nxt_thresh - total
    else:
        nxt_name  = None
        progress  = 1.0
        keys_left = 0

    wlvl_idx  = get_level_idx(total_words, WORD_LEVELS)
    wlvl_name = WORD_LEVELS[wlvl_idx][1]
    if wlvl_idx + 1 < len(WORD_LEVELS):
        wnxt_thresh, wnxt_name = WORD_LEVELS[wlvl_idx + 1]
        wcur_thresh            = WORD_LEVELS[wlvl_idx][0]
        wprogress              = (total_words - wcur_thresh) / (wnxt_thresh - wcur_thresh)
        words_left             = wnxt_thresh - total_words
    else:
        wnxt_name  = None
        wprogress  = 1.0
        words_left = 0

    # ── level block ──
    lvl_text = Text()
    lvl_text.append(f"  Level {lvl_idx + 1}  ", style="bold bright_yellow")
    lvl_text.append(f"{lvl_name}\n\n", style="bold white")
    lvl_text.append(f"  {total:,}", style="bold cyan")
    lvl_text.append(" keypresses  ", style="dim")
    lvl_text.append(f"{total_words:,}", style="bold bright_blue")
    lvl_text.append(" words  ", style="dim")
    lvl_text.append(f"(+{WORD_BONUS} pts each)\n", style="dim")
    lvl_text.append(f"  {balance:,}", style="bold yellow")
    lvl_text.append(" pts  ", style="dim")
    lvl_text.append(f"{ppt} pt/key\n\n", style="magenta")

    bar_width = 36
    filled    = int(bar_width * min(progress, 1.0))
    bar       = "█" * filled + "░" * (bar_width - filled)
    lvl_text.append(f"  [{bar}] {progress*100:.1f}%\n", style="cyan")
    if nxt_name:
        lvl_text.append(f"  {keys_left:,} keys until ", style="dim")
        lvl_text.append(nxt_name, style="bright_white")
    else:
        lvl_text.append("  MAX LEVEL REACHED", style="bold bright_yellow")

    lvl_text.append(f"\n\n  Word Rank {wlvl_idx + 1}  ", style="bold bright_magenta")
    lvl_text.append(f"{wlvl_name}\n", style="bold white")
    wfilled = int(bar_width * min(wprogress, 1.0))
    wbar    = "█" * wfilled + "░" * (bar_width - wfilled)
    lvl_text.append(f"  [{wbar}] {wprogress*100:.1f}%\n", style="bright_blue")
    if wnxt_name:
        lvl_text.append(f"  {words_left:,} words until ", style="dim")
        lvl_text.append(wnxt_name, style="bright_white")
    else:
        lvl_text.append("  MAX WORD RANK REACHED", style="bold bright_magenta")

    # ── last 7 days ──
    days_text = Text()
    days_text.append("  Last 7 days\n\n", style="bold dim")
    sorted_days = sorted(daily.items())[-7:]
    if sorted_days:
        max_val = max(v for _, v in sorted_days) or 1
        for day, count in sorted_days:
            bar_len = max(1, int(20 * count / max_val))
            days_text.append(f"  {day[5:]}  ", style="dim")
            days_text.append("▓" * bar_len, style="blue")
            days_text.append(f"  {count:,}\n", style="dim")
    else:
        days_text.append("  No data yet\n", style="dim")

    top = Table(box=None, show_header=False, padding=(0, 0), expand=True)
    top.add_column(ratio=3)
    top.add_column(ratio=2)
    top.add_row(lvl_text, days_text)

    # ── shop ──
    shop = Text()
    shop.append("  SHOP", style="bold bright_magenta")
    shop.append("  — press 1–6 to buy\n\n", style="dim")
    for i, (uid, name, desc, cost, _) in enumerate(UPGRADES):
        slot = str(i + 1)
        if uid in owned:
            shop.append(f"  [{slot}] ", style="dim")
            shop.append(f"✓ {name:<18}", style="bold green")
            shop.append(f" {desc}\n", style="dim green")
        elif i > 0 and upgrade_ids[i - 1] not in owned:
            shop.append(f"  [{slot}] ", style="dim")
            shop.append(f"  {name:<18}", style="dim")
            shop.append(f" {desc}  🔒\n", style="dim")
        else:
            affordable = balance >= cost
            c = "bold yellow" if affordable else "dim white"
            shop.append(f"  [{slot}] ", style="bold" if affordable else "dim")
            shop.append(f"  {name:<18}", style=c)
            shop.append(f" {desc}", style="dim")
            shop.append(f"  {cost:,} pts\n", style=c)

    # ── message bar ──
    msg_row = Text()
    if message:
        msg_row.append(f"\n  {message}\n", style="bold bright_green")

    # ── achievements ──
    ach = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    for key, title, desc in ACHIEVEMENTS:
        if key in unlocked:
            ach.add_row("  ✓", f"[bold green]{title}[/]", f"[dim]{desc}[/]")
        else:
            ach.add_row("  [dim]·[/]", f"[dim]{title}[/]", f"[dim]{desc}[/]")

    running, pid = is_daemon_running()
    status = (
        f"[green]● tracking[/] pid {pid}"
        if running
        else "[red]● not tracking[/]  —  run: python idler.py start"
    )

    return Panel(
        Group(top, Text(""), shop, msg_row, ach),
        title=f"[bold cyan]⌨  KEY IDLER[/]   {status}",
        border_style="cyan",
    )


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_start():
    running, pid = is_daemon_running()
    if running:
        print(f"Daemon already running (PID {pid})")
        return

    import subprocess
    script = os.path.abspath(__file__)

    if sys.platform == "win32":
        # CREATE_NO_WINDOW keeps the process in the session (needed for the
        # WH_KEYBOARD_LL message pump); CREATE_NEW_PROCESS_GROUP stops
        # Ctrl+C from the parent terminal propagating to the daemon.
        CREATE_NO_WINDOW      = 0x08000000
        CREATE_NEW_PROC_GROUP = 0x00000200
        proc = subprocess.Popen(
            [sys.executable, script, "--daemon"],
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROC_GROUP,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, script, "--daemon"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

    time.sleep(0.8)
    running2, pid2 = is_daemon_running()
    print(f"Daemon started (PID {pid2 or proc.pid})")
    print("Tracking keypresses across all apps.")


def cmd_stop():
    running, pid = is_daemon_running()
    if not running:
        print("Daemon not running.")
        return
    try:
        if sys.platform == "win32":
            import subprocess
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            import signal
            os.kill(pid, signal.SIGTERM)
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        print("Daemon stopped.")
    except OSError:
        print("Could not stop daemon (may have already exited).")
        try:
            PID_FILE.unlink()
        except OSError:
            pass


def cmd_stats():
    cmd_live()


def cmd_live():
    require_rich()
    from rich.console import Console
    from rich.live    import Live

    running, _ = is_daemon_running()
    if not running:
        cmd_start()

    console   = Console()
    msg_text  = [None]
    msg_time  = [0.0]
    stop_flag = [False]

    def buy(slot_char):
        idx = int(slot_char) - 1
        if 0 <= idx < len(UPGRADES):
            _, text = try_buy_upgrade(UPGRADES[idx][0])
            msg_text[0] = text
            msg_time[0] = time.time()

    def input_loop():
        if sys.platform == "win32":
            import msvcrt
            while not stop_flag[0]:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in "123456":
                        buy(ch)
                    elif ch.lower() in ("q", "\x03"):
                        stop_flag[0] = True
                        break
                time.sleep(0.05)
        else:
            import tty, termios, select
            fd  = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_flag[0]:
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        ch = sys.stdin.read(1)
                        if ch in "123456":
                            buy(ch)
                        elif ch.lower() in ("q", "\x03"):
                            stop_flag[0] = True
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    Thread(target=input_loop, daemon=True).start()

    with Live(build_panel(), refresh_per_second=2, console=console) as live:
        try:
            while not stop_flag[0]:
                time.sleep(0.5)
                msg = msg_text[0] if msg_text[0] and (time.time() - msg_time[0]) < 3.0 else None
                if not msg:
                    msg_text[0] = None
                live.update(build_panel(msg))
        except KeyboardInterrupt:
            stop_flag[0] = True


def cmd_reset():
    confirm = input("Reset ALL keyidler data? Type 'yes' to confirm: ").strip().lower()
    if confirm == "yes":
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        print("Data reset.")
    else:
        print("Cancelled.")


# ── entry ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="idler",
        description="Key Idler — your keypresses, gamified",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("start", help="start background key-tracking daemon")
    sub.add_parser("stop",  help="stop the daemon")
    sub.add_parser("stats", help="show stats (static snapshot)")
    sub.add_parser("live",  help="live-updating dashboard (default)")
    sub.add_parser("reset", help="wipe all data and start over")
    parser.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
        return

    dispatch = {
        "start": cmd_start,
        "stop":  cmd_stop,
        "stats": cmd_stats,
        "live":  cmd_live,
        "reset": cmd_reset,
    }

    fn = dispatch.get(args.cmd)
    if fn:
        fn()
    else:
        cmd_live()


if __name__ == "__main__":
    main()
