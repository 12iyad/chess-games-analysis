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
