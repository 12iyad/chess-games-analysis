"""SQLite schema and helpers for chess analysis."""
import sqlite3
from pathlib import Path

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    white_username TEXT NOT NULL,
    black_username TEXT NOT NULL,
    white_result TEXT,
    black_result TEXT,
    time_control TEXT,
    time_class TEXT,
    rules TEXT,
    pgn TEXT NOT NULL,
    fen_final TEXT,
    end_time INTEGER,
    move_count INTEGER,
    your_color TEXT,
    result_for_you TEXT,
    opening_name TEXT
);

CREATE TABLE IF NOT EXISTS key_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    event_type TEXT NOT NULL,
    move_number INTEGER NOT NULL,
    side_affected TEXT,
    side_causing TEXT,
    piece_involved TEXT,
    phase TEXT,
    UNIQUE(game_id, event_type, move_number)
);

CREATE TABLE IF NOT EXISTS loss_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL UNIQUE REFERENCES games(id),
    first_major_loss_move INTEGER,
    piece_lost_first TEXT,
    phase_of_collapse TEXT,
    checkmating_piece TEXT,
    your_color TEXT
);

CREATE INDEX IF NOT EXISTS idx_key_events_game ON key_events(game_id);
CREATE INDEX IF NOT EXISTS idx_key_events_type ON key_events(event_type);
CREATE INDEX IF NOT EXISTS idx_games_result ON games(result_for_you);
"""


def get_connection(path: str | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str | None = None) -> None:
    conn = get_connection(path)
    conn.executescript(_SCHEMA)
    try:
        conn.execute("ALTER TABLE games ADD COLUMN opening_name TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.close()


def insert_game(
    conn: sqlite3.Connection,
    *,
    url: str,
    white_username: str,
    black_username: str,
    white_result: str,
    black_result: str,
    time_control: str,
    time_class: str,
    rules: str,
    pgn: str,
    fen_final: str | None,
    end_time: int | None,
    move_count: int,
    your_color: str,
    result_for_you: str,
    opening_name: str = "",
) -> int | None:
    conn.execute(
        """
        INSERT OR IGNORE INTO games (
            url, white_username, black_username, white_result, black_result,
            time_control, time_class, rules, pgn, fen_final, end_time, move_count,
            your_color, result_for_you, opening_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            url,
            white_username,
            black_username,
            white_result,
            black_result,
            time_control,
            time_class,
            rules,
            pgn,
            fen_final,
            end_time,
            move_count,
            your_color,
            result_for_you,
            opening_name,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM games WHERE url = ?", (url,)).fetchone()
    return row["id"] if row else None


def update_game_move_count(conn: sqlite3.Connection, game_id: int, move_count: int) -> None:
    conn.execute("UPDATE games SET move_count = ? WHERE id = ?", (move_count, game_id))
    conn.commit()


def update_game_opening(conn: sqlite3.Connection, game_id: int, opening_name: str) -> None:
    conn.execute("UPDATE games SET opening_name = ? WHERE id = ?", (opening_name or "", game_id))
    conn.commit()


def get_game_id_by_url(conn: sqlite3.Connection, url: str) -> int | None:
    row = conn.execute("SELECT id FROM games WHERE url = ?", (url,)).fetchone()
    return row["id"] if row else None


def insert_key_event(
    conn: sqlite3.Connection,
    game_id: int,
    event_type: str,
    move_number: int,
    *,
    side_affected: str | None = None,
    side_causing: str | None = None,
    piece_involved: str | None = None,
    phase: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO key_events (
            game_id, event_type, move_number, side_affected, side_causing, piece_involved, phase
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (game_id, event_type, move_number, side_affected, side_causing, piece_involved, phase),
    )


def insert_loss_summary(
    conn: sqlite3.Connection,
    game_id: int,
    *,
    first_major_loss_move: int | None = None,
    piece_lost_first: str | None = None,
    phase_of_collapse: str | None = None,
    checkmating_piece: str | None = None,
    your_color: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO loss_summaries (
            game_id, first_major_loss_move, piece_lost_first, phase_of_collapse,
            checkmating_piece, your_color
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (game_id, first_major_loss_move, piece_lost_first, phase_of_collapse, checkmating_piece, your_color),
    )


def get_all_games_for_ingest(conn: sqlite3.Connection):
    """Return rows with id, pgn, your_color, result_for_you, white_username, black_username."""
    return conn.execute(
        "SELECT id, pgn, your_color, result_for_you, white_username, black_username FROM games"
    ).fetchall()


def clear_events_for_game(conn: sqlite3.Connection, game_id: int) -> None:
    conn.execute("DELETE FROM key_events WHERE game_id = ?", (game_id,))
    conn.execute("DELETE FROM loss_summaries WHERE game_id = ?", (game_id,))
    conn.commit()


def _year_ts_bounds(year: int) -> tuple[int, int]:
    import datetime
    start = int(datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    end = int(datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    return start, end


def get_losses_for_year(conn: sqlite3.Connection, year: int):
    """Losses in given year with loss_summary and game opening, for reasoning report."""
    start_ts, end_ts = _year_ts_bounds(year)
    return conn.execute(
        """
        SELECT
            g.id, g.your_color, g.opening_name, g.time_class,
            g.move_count, g.end_time,
            ls.first_major_loss_move, ls.piece_lost_first,
            ls.phase_of_collapse, ls.checkmating_piece
        FROM games g
        JOIN loss_summaries ls ON ls.game_id = g.id
        WHERE g.result_for_you = 'loss'
          AND g.end_time >= ? AND g.end_time < ?
        ORDER BY g.your_color, g.opening_name, g.id
        """,
        (start_ts, end_ts),
    ).fetchall()


def get_games_count_for_year(conn: sqlite3.Connection, year: int) -> tuple[int, int, int]:
    """Return (total, wins, losses) for the given year."""
    start_ts, end_ts = _year_ts_bounds(year)
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN result_for_you = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result_for_you = 'loss' THEN 1 ELSE 0 END) AS losses
        FROM games
        WHERE end_time >= ? AND end_time < ?
        """,
        (start_ts, end_ts),
    ).fetchone()
    return (row["total"] or 0, row["wins"] or 0, row["losses"] or 0)


def get_opening_stats_for_year(conn: sqlite3.Connection, year: int):
    """Per (opening_name, your_color): total, wins, losses. Opening name normalized (empty -> Other)."""
    start_ts, end_ts = _year_ts_bounds(year)
    return conn.execute(
        """
        SELECT
            COALESCE(NULLIF(TRIM(opening_name), ''), 'Other') AS opening_name,
            your_color,
            COUNT(*) AS total,
            SUM(CASE WHEN result_for_you = 'win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result_for_you = 'loss' THEN 1 ELSE 0 END) AS losses
        FROM games
        WHERE end_time >= ? AND end_time < ?
        GROUP BY opening_name, your_color
        ORDER BY your_color, opening_name
        """,
        (start_ts, end_ts),
    ).fetchall()


def get_losses_with_queen_events(conn: sqlite3.Connection):
    """Return loss_summaries joined with queen_lost key_events (by your_color)."""
    return conn.execute(
        """
        SELECT
            g.id AS game_id,
            g.move_count,
            g.your_color,
            g.time_class,
            ls.first_major_loss_move,
            ls.piece_lost_first,
            ls.phase_of_collapse,
            ls.checkmating_piece,
            ke.move_number AS queen_lost_move,
            ke.phase AS queen_lost_phase
        FROM games g
        JOIN loss_summaries ls ON ls.game_id = g.id
        LEFT JOIN key_events ke ON ke.game_id = g.id AND ke.event_type = 'queen_lost' AND ke.side_affected = g.your_color
        WHERE g.result_for_you = 'loss'
        ORDER BY g.id
        """
    ).fetchall()
