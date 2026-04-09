# chess-games-analysis

Analysing chess games at scale to find weaknesses: which pieces you lose first, when you lose your queen, what checkmates you, and which phase you collapse in.

## Setup

```bash
pip install -r requirements.txt
```

Optional: set `CHESS_USERNAME`, `CHESS_DB`, and `YEAR_FILTER` in `config.py` (default: `12iyad`, `chess_analysis.db`, `2026`). Set `YEAR_FILTER = None` to analyze all years.

## Run

```bash
python run.py
```

This will:

1. **Fetch** – Download your games from the Chess.com API (only the year in `YEAR_FILTER`, e.g. 2026) and store them in SQLite.
2. **Ingest** – Parse each PGN, detect key events and **openings** (London, Caro-Kann, or Other from first moves).
3. **Queen-loss report** – How often you lose your queen in losses, move range, phase, first piece lost, what checkmates you.
4. **Why I'm losing report** – In-depth reasoning for the chosen year: **why you lose as White vs Black**, and **why your openings failed** (London/Caro-Kann loss rate and where you collapse in each).

## Project layout

- `config.py` – Username, DB path, `YEAR_FILTER` (e.g. 2026), phase boundaries.
- `db.py` – SQLite schema (games with opening_name, key_events, loss_summaries) and helpers.
- `fetch.py` – Chess.com API → games table (filtered by year).
- `ingest.py` – PGN → move replay, event detection, opening detection (London/Caro-Kann), loss summaries.
- `report.py` – Queen-loss weakness report.
- `report_why_losing.py` – Why I'm losing (by color and opening) for the filtered year.
- `run.py` – Runs fetch → ingest → queen report → why-losing report.

## v1 weakness focus

The first report answers:

- In what share of losses do you lose your queen?
- When do you lose it (opening / 11–20 / 21–30 / etc.)?
- What phase do you usually collapse in?
- What piece do you lose first (Q/R/B/N)?
- What piece checkmates you most?

From that you get a concrete training hint (e.g. queen safety and early tactics).

---

### Example response from terminal run (don't judge my blunders)
```console
Filtering to year 2026 only.

Step 1: Fetching games from Chess.com...
  Stored 497 games.

Step 2: Ingesting (parsing PGNs, detecting events, opening detection)...
  Processed 1083 games.

Step 3: Queen-loss weakness report

============================================================
  QUEEN LOSS WEAKNESS REPORT (v1)
  Focus: when and how often you lose your queen in losses
============================================================
  Player: 12iyad
  Total losses analyzed: 499

  --- Queen in losses ---
  In 341 of 499 losses you lost your queen (68%).
  When you lost your queen (move range):
    1-10 (opening): 48 games
    11-20: 134 games
    21-30: 91 games
    31-40: 45 games
    41+: 23 games
  Phase when you lost your queen:
    opening: 48 games
    middlegame: 236 games
    endgame: 57 games

  --- First major piece lost (all losses) ---
    First piece lost = Q: 48 games
    First piece lost = R: 32 games
    First piece lost = B: 177 games
    First piece lost = N: 213 games
    First piece lost = -: 29 games

  --- Phase where collapse started ---
    opening: 323 games
    middlegame: 147 games
    -: 29 games

  --- What checkmated you ---
    Q: 123 games
    R: 62 games
    B: 9 games
    P: 8 games
    N: 6 games

  -> Training hint: if queen loss is high in opening/early middlegame,
    focus on queen safety and early tactics (pins, forks) in your prep.
============================================================

Step 4: Why I'm losing (White vs Black, opening failure reasoning)

================================================================
  WHY I'M LOSING - 2026 (White vs Black, opening failure reasoning)
================================================================
  Player: 12iyad
  Year: 2026  |  Games: 497  (W: 242, L: 222, D: 33)

  --- WHAT IS 'COLLAPSE'? ---
  Collapse = the first time you lose a real piece (Queen, Rook, Bishop, or Knight).
  That move is where the game usually starts to slip. We track:
  - which phase (opening / middlegame / endgame), which piece, and around which move.

  --- MOST COMMON COLLAPSE SCENARIOS (all losses this year) ---
  Ranked by how often this exact pattern happened:

   1. Opening + lost Bishop first (moves 1-10): 83 games (37%)
   2. Opening + lost Knight first (moves 1-10): 73 games (33%)
   3. Middlegame + lost Bishop first (moves 11-20): 25 games (11%)
   4. Middlegame + lost Knight first (moves 11-20): 24 games (11%)
   5. Opening + lost Queen first (moves 1-10): 5 games (2%)
   6. Opening + lost Rook first (moves 1-10): 5 games (2%)
   7. Middlegame + lost Queen first (moves 11-20): 3 games (1%)
   8. Middlegame + lost Rook first (moves 11-20): 1 games (0%)
   9. Middlegame + lost Knight first (moves 21-30): 1 games (0%)

  -> Your #1 pattern: losing a Bishop in the opening (moves 1-10), 37% of losses.
     Focus training on that phase and piece (e.g. bishop safety in the opening, knight tactics).

  --- LOSING AS WHITE ---
  Total losses as White: 115
  - Collapse usually starts in the opening (81% of these losses).
  - You most often lose a Bishop first (50%).
  - You are most often checkmated by a Queen (23%).
  Most common scenario as White: Opening + lost Bishop first (moves 1-10) - 49 games

  --- LOSING AS BLACK ---
  Total losses as Black: 107
  - Collapse usually starts in the opening (68% of these losses).
  - You most often lose a Knight first (47%).
  - You are most often checkmated by a Queen (32%).
  Most common scenario as Black: Opening + lost Knight first (moves 1-10) - 34 games

  --- OPENING FAILURE (why your openings failed) ---
  [Caro-Kann] as Black: 54 games, 24 losses (44% loss rate)
  - Collapse usually starts in the opening (71% of these losses).
  - You most often lose a Bishop first (54%).
  - You are most often checkmated by a Queen (33%).

  [London] as Black: 21 games, 8 losses (38% loss rate)
  - Collapse usually starts in the opening (88% of these losses).
  - You most often lose a Knight first (38%).
  - You are most often checkmated by a Queen (38%).

  [Other] as Black: 171 games, 75 losses (44% loss rate)
  - Collapse usually starts in the opening (65% of these losses).
  - You most often lose a Knight first (51%).
  - You are most often checkmated by a Queen (31%).

  [London] as White: 236 games, 107 losses (45% loss rate)
  - Collapse usually starts in the opening (82% of these losses).
  - You most often lose a Bishop first (51%).
  - You are most often checkmated by a Queen (23%).

  [Other] as White: 15 games, 8 losses (53% loss rate)
  - Collapse usually starts in the opening (62% of these losses).
  - You most often lose a Knight first (50%).
  - You are most often checkmated by a Knight (12%).

  -> Use this to see: London/Caro-Kann loss rate and where you collapse in each.
================================================================
```
