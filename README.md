# idle-typer-cli

An idle game powered by your **real keypresses** across every app on your computer.

Run it once, forget about it, and check back later to see your level, achievements, and spend points in the upgrade shop — all from the terminal.

---

## How it works

A lightweight background daemon listens for global keypresses (via [pynput](https://pypi.org/project/pynput/)) and flushes counts to `~/.keyidler/data.json` every 5 seconds. It tracks:

- **Total keypresses** — your all-time key count, used to calculate your typing level
- **Words typed** — word boundaries are detected via space/enter/tab; words earn bonus points
- **Points** — earned at a rate of `keypresses × (base 1 + upgrade bonuses) + words × 10`
- **Daily history** — per-day key counts for the activity chart
- **Active hours** — which hours of the day you type, used for Night Owl / Early Bird achievements

The stats dashboard (`python idler.py` or `python idler.py live`) auto-refreshes twice per second and lets you spend points in the upgrade shop by pressing **1–6**.

---

## Requirements

```
pip install pynput rich
```

Python 3.8+ required. Works on **Windows**, **macOS**, and **Linux**.

> On Linux/macOS the daemon may need to run as root (or with input-device permissions) for the global keyboard hook to work.

---

## Usage

| Command | Description |
|---|---|
| `python idler.py` | Open the live dashboard (starts daemon automatically) |
| `python idler.py start` | Start the background daemon only |
| `python idler.py stop` | Stop the daemon |
| `python idler.py stats` | Same as `live` — open the dashboard |
| `python idler.py reset` | Wipe all data and start fresh |

Press **Q** or **Ctrl+C** inside the dashboard to exit (the daemon keeps running in the background).

---

## Levels

There are 21 typing levels based on total keypresses, from **Sleeping Fingers** (0 keys) up to **The Infinite** (10 M) and **Beyond Mortal** (25 M). A separate **Word Rank** track (15 ranks) runs alongside it, from **Silent** up to **Transcendent Scribe**.

---

## Upgrade Shop

Six upgrades unlock in sequence, each adding a flat bonus to your points-per-keypress:

| # | Name | Bonus | Cost |
|---|---|---|---|
| 1 | Nimble Fingers | +1 pt/key | 100 pts |
| 2 | Touch Typist | +2 pt/key | 400 pts |
| 3 | Speed Freak | +5 pt/key | 1,500 pts |
| 4 | Keyboard Wizard | +10 pt/key | 6,000 pts |
| 5 | Type God | +25 pt/key | 25,000 pts |
| 6 | Transcendent | +50 pt/key | 100,000 pts |

With all upgrades owned you earn **94 pts/key** plus the 10-point word bonus.

---

## Achievements

| Achievement | Condition |
|---|---|
| Baby Steps | 100 total keys |
| Kilokeys | 1,000 total keys |
| Ten Thousand | 10,000 total keys |
| The Centurion | 100,000 total keys |
| Million Keys | 1,000,000 total keys |
| Night Owl | Typed past midnight |
| Early Bird | Typed before 6 am |
| Marathon | 1,000 keys in one day |
| Century Day | 10,000 keys in one day |
| Week Warrior | Typed on 7 different days |
| Monthly Regular | Typed on 30 different days |

---

## Data storage

All data lives in `~/.keyidler/data.json`. The daemon PID is stored in `~/.keyidler/daemon.pid` while running. You can back up or inspect the JSON file freely — the schema is straightforward.

---

## Example stats screen

```
╭─────────────────────────────────────────────────────────────────────────────────╮
│  ⌨  KEY IDLER   ● tracking  pid 18432                                           │
│                                                                                  │
│  Level 8  Keyboard Regular          Last 7 days                                 │
│                                                                                  │
│  43,812 keypresses  2,104 words  (+10 pts each)    06-12  ▓▓▓▓▓▓▓▓▓▓  8,210    │
│  18,540 pts  3 pt/key                              06-13  ▓▓▓▓▓▓       5,100    │
│                                                    06-14  ▓▓           1,300    │
│  [████████████████████░░░░░░░░░░░░░░] 48.5%        06-15  ▓▓▓▓▓▓▓▓▓▓▓ 9,800    │
│  36,188 keys until Speed Demon                     06-16  ▓▓▓▓▓        4,200    │
│                                                    06-17  ▓▓▓▓▓▓▓▓     6,900    │
│  Word Rank 5  Casual Conversant                    06-18  ▓▓▓▓▓▓▓▓▓▓▓ 9,100    │
│  [████████████░░░░░░░░░░░░░░░░░░░░░░] 32.8%                                     │
│  2,396 words until Essay Crafter                                                 │
│                                                                                  │
│  SHOP  — press 1–6 to buy                                                        │
│                                                                                  │
│  [1]  ✓ Nimble Fingers     +1 pt/key                                             │
│  [2]  ✓ Touch Typist       +2 pt/key                                             │
│  [3]    Speed Freak        +5 pt/key    1,500 pts                                │
│  [4]    Keyboard Wizard    +10 pt/key   6,000 pts                                │
│  [5]    Type God           +25 pt/key   25,000 pts  🔒                           │
│  [6]    Transcendent       +50 pt/key   100,000 pts  🔒                          │
│                                                                                  │
│    ✓  Baby Steps        100 total keys                                           │
│    ✓  Kilokeys          1,000 total keys                                         │
│    ✓  Ten Thousand      10,000 total keys                                        │
│    ·  The Centurion     100,000 total keys                                       │
│    ·  Million Keys      1,000,000 total keys                                     │
│    ✓  Night Owl         typed past midnight                                      │
│    ·  Early Bird        typed before 6am                                         │
│    ✓  Marathon          1,000 keys in one day                                    │
│    ✓  Century Day       10,000 keys in one day                                   │
│    ✓  Week Warrior      typed on 7 different days                                │
│    ·  Monthly Regular   typed on 30 different days                               │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

---

## License

MIT
