"""Fetch games from Chess.com API and persist to SQLite."""
import time
import requests

from config import API_BASE, USER_AGENT, USERNAME, YEAR_FILTER
from db import get_connection, init_db, insert_game

HEADERS = {"User-Agent": USER_AGENT}


def _result_for_you(my_result: str) -> str:
    if my_result == "win":
        return "win"
    if my_result in ("loss", "checkmated", "resigned", "timeout", "lose"):
        return "loss"
    return "draw"


def _time_class(time_control: str) -> str:
    if not time_control:
        return "unknown"
    # PGN format e.g. "300+2" (seconds) or "1/86400" (daily)
    parts = time_control.split("+")
    try:
        base = int(parts[0])
    except ValueError:
        return "unknown"
    if base >= 86400 or base == 0:  # daily
        return "daily"
    if base < 180:
        return "bullet"
    if base < 600:
        return "blitz"
    if base < 3600:
        return "rapid"
    return "daily"


def fetch_archives() -> list[str]:
    url = f"{API_BASE}/player/{USERNAME}/games/archives"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data.get("archives", [])


def fetch_month_games(archive_url: str) -> list[dict]:
    r = requests.get(archive_url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data.get("games", [])


def _archive_in_year(archive_url: str, year: int) -> bool:
    """Archive URL is like .../games/2025/11 - check year."""
    parts = archive_url.rstrip("/").split("/")
    if len(parts) >= 2:
        try:
            return int(parts[-2]) == year
        except ValueError:
            pass
    return False


def run_fetch() -> int:
    init_db()
    archives = fetch_archives()
    if not archives:
        print("No archives found.")
        return 0
    if YEAR_FILTER is not None:
        archives = [u for u in archives if _archive_in_year(u, YEAR_FILTER)]
        if not archives:
            print(f"No archives for year {YEAR_FILTER}.")
            return 0
    conn = get_connection()
    total = 0
    # 2026 bounds for per-game filter (end_time)
    start_ts = 1767225600 if YEAR_FILTER == 2026 else 0
    end_ts = 1798761600 if YEAR_FILTER == 2026 else 10**12
    if YEAR_FILTER not in (None, 2026):
        from db import _year_ts_bounds
        start_ts, end_ts = _year_ts_bounds(YEAR_FILTER)
    for archive_url in archives:
        games = fetch_month_games(archive_url)
        for g in games:
            white = g.get("white") or {}
            black = g.get("black") or {}
            white_username = (white.get("username") or "").strip() or "?"
            black_username = (black.get("username") or "").strip() or "?"
            white_result = (white.get("result") or "").strip()
            black_result = (black.get("result") or "").strip()
            pgn = g.get("pgn") or ""
            if not pgn:
                continue
            url = g.get("url") or ""
            if not url:
                continue
            me = USERNAME.lower()
            if white_username.lower() == me:
                your_color = "white"
                my_result = white_result
            elif black_username.lower() == me:
                your_color = "black"
                my_result = black_result
            else:
                continue  # game doesn't involve us
            result_for_you = _result_for_you(my_result)
            time_control = (g.get("time_control") or "").strip()
            time_class = _time_class(time_control)
            rules = (g.get("rules") or "chess").strip()
            fen_final = (g.get("fen") or "").strip() or None
            end_time = g.get("end_time")
            if YEAR_FILTER is not None and (end_time is None or end_time < start_ts or end_time >= end_ts):
                continue
            opening_name = ""
            eco = g.get("eco")
            if isinstance(eco, str) and "openings/" in eco:
                opening_name = eco.split("openings/")[-1].replace("-", " ").strip() or ""
            insert_game(
                conn,
                url=url,
                white_username=white_username,
                black_username=black_username,
                white_result=white_result,
                black_result=black_result,
                time_control=time_control,
                time_class=time_class,
                rules=rules,
                pgn=pgn,
                fen_final=fen_final,
                end_time=end_time,
                move_count=0,  # ingest will fill
                your_color=your_color,
                result_for_you=result_for_you,
                opening_name=opening_name,
            )
            total += 1
        time.sleep(0.2)
    conn.close()
    return total
