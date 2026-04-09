"""Why I'm losing: in-depth reasoning by color and opening (2026 only)."""
from collections import defaultdict

from config import USERNAME, YEAR_FILTER
from db import (
    get_connection,
    get_games_count_for_year,
    get_losses_for_year,
    get_opening_stats_for_year,
)


def _norm_opening(name: str | None) -> str:
    return (name or "").strip() or "Other"


def _reasoning_blurb(phase_counts: dict, piece_counts: dict, mate_counts: dict, n: int) -> list[str]:
    """Bullet-point reasoning from aggregated loss data."""
    lines = []
    if n == 0:
        return lines
    if phase_counts:
        top_phase = max(phase_counts, key=phase_counts.get)
        pct = 100 * phase_counts[top_phase] / n
        lines.append(f"  - Collapse usually starts in the {top_phase} ({pct:.0f}% of these losses).")
    if piece_counts:
        top_piece = max((k for k in piece_counts if k != "-"), key=lambda k: piece_counts.get(k, 0), default=None)
        if top_piece:
            pct = 100 * piece_counts[top_piece] / n
            lines.append(f"  - You most often lose a {_piece_name(top_piece)} first ({pct:.0f}%).")
    if mate_counts:
        top_mate = max(mate_counts, key=mate_counts.get)
        pct = 100 * mate_counts[top_mate] / n
        lines.append(f"  - You are most often checkmated by a {_piece_name(top_mate)} ({pct:.0f}%).")
    return lines


def _piece_name(symbol: str) -> str:
    return {"Q": "Queen", "R": "Rook", "B": "Bishop", "N": "Knight", "P": "Pawn", "K": "King"}.get(symbol, symbol)


def _move_band(move: int | None) -> str:
    if move is None:
        return "?"
    if move <= 10:
        return "1-10"
    if move <= 20:
        return "11-20"
    if move <= 30:
        return "21-30"
    if move <= 40:
        return "31-40"
    return "41+"


def _collapse_scenario_key(phase: str | None, piece: str | None, move: int | None) -> tuple[str, str, str]:
    """(phase, piece_lost, move_band) for grouping."""
    return (
        (phase or "?").strip(),
        (piece or "?").strip(),
        _move_band(move),
    )


def run_why_losing_report() -> None:
    year = YEAR_FILTER
    if year is None:
        print("  Set config YEAR_FILTER (e.g. 2026) to run this report.")
        return
    conn = get_connection()
    total, wins, losses = get_games_count_for_year(conn, year)
    if total == 0:
        print(f"  No games in {year}. Run fetch with YEAR_FILTER={year}.")
        conn.close()
        return
    loss_rows = get_losses_for_year(conn, year)
    opening_stats = get_opening_stats_for_year(conn, year)
    conn.close()

    # Group losses by your_color
    by_color: dict[str, list] = defaultdict(list)
    for r in loss_rows:
        by_color[r["your_color"]].append(r)

    # Group losses by (your_color, opening_name)
    by_opening: dict[tuple[str, str], list] = defaultdict(list)
    for r in loss_rows:
        opening = _norm_opening(r["opening_name"])
        by_opening[(r["your_color"], opening)].append(r)

    opening_totals: dict[tuple[str, str], tuple[int, int, int]] = {}
    for row in opening_stats:
        opening = _norm_opening(row["opening_name"])
        key = (row["your_color"], opening)
        opening_totals[key] = (row["total"], row["wins"], row["losses"])

    print()
    print("=" * 64)
    print(f"  WHY I'M LOSING - {year} (White vs Black, opening failure reasoning)")
    print("=" * 64)
    print(f"  Player: {USERNAME}")
    print(f"  Year: {year}  |  Games: {total}  (W: {wins}, L: {losses}, D: {total - wins - losses})")
    print()
    print("  --- WHAT IS 'COLLAPSE'? ---")
    print("  Collapse = the first time you lose a real piece (Queen, Rook, Bishop, or Knight).")
    print("  That move is where the game usually starts to slip. We track:")
    print("  - which phase (opening / middlegame / endgame), which piece, and around which move.")
    print()

    # --- Most common collapse scenarios (phase + piece + move band) ---
    scenario_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for r in loss_rows:
        phase = (r["phase_of_collapse"] or "").strip() or "?"
        piece = (r["piece_lost_first"] or "").strip() or "?"
        if phase == "?" and piece == "?":
            continue
        move = r["first_major_loss_move"]
        key = (phase, piece, _move_band(move))
        scenario_counts[key] += 1

    n_losses = len(loss_rows)
    if n_losses and scenario_counts:
        print("  --- MOST COMMON COLLAPSE SCENARIOS (all losses this year) ---")
        print("  Ranked by how often this exact pattern happened:")
        print()
        sorted_scenarios = sorted(
            scenario_counts.items(),
            key=lambda x: -x[1],
        )
        for i, ((phase, piece, band), count) in enumerate(sorted_scenarios[:15], 1):
            pct = 100 * count / n_losses
            piece_str = _piece_name(piece) if piece != "?" else "piece"
            phase_str = phase if phase != "?" else "?"
            print(f"  {i:2}. {phase_str.capitalize()} + lost {piece_str} first (moves {band}): {count} games ({pct:.0f}%)")
        print()
        top_phase, top_piece, top_band = sorted_scenarios[0][0]
        top_count = sorted_scenarios[0][1]
        top_pct = 100 * top_count / n_losses
        print(f"  -> Your #1 pattern: losing a {_piece_name(top_piece)} in the {top_phase} (moves {top_band}), {top_pct:.0f}% of losses.")
        print("     Focus training on that phase and piece (e.g. bishop safety in the opening, knight tactics).")
    print()

    # --- Section: Losing as White ---
    white_losses = by_color.get("white", [])
    n_white = len(white_losses)
    print("  --- LOSING AS WHITE ---")
    if n_white == 0:
        print("  No losses as White in this period.")
    else:
        phase = defaultdict(int)
        piece = defaultdict(int)
        mate = defaultdict(int)
        white_scenarios: dict[tuple[str, str, str], int] = defaultdict(int)
        for r in white_losses:
            phase[r["phase_of_collapse"] or "-"] += 1
            piece[r["piece_lost_first"] or "-"] += 1
            if r["checkmating_piece"]:
                mate[r["checkmating_piece"]] += 1
            ph, pc, band = _collapse_scenario_key(r["phase_of_collapse"], r["piece_lost_first"], r["first_major_loss_move"])
            if ph != "?" or pc != "?":
                white_scenarios[(ph, pc, band)] += 1
        print(f"  Total losses as White: {n_white}")
        for line in _reasoning_blurb(phase, piece, mate, n_white):
            print(line)
        if white_scenarios:
            top = max(white_scenarios.items(), key=lambda x: x[1])
            (ph, pc, band), cnt = top
            print(f"  Most common scenario as White: {ph.capitalize()} + lost {_piece_name(pc)} first (moves {band}) - {cnt} games")
    print()

    # --- Section: Losing as Black ---
    black_losses = by_color.get("black", [])
    n_black = len(black_losses)
    print("  --- LOSING AS BLACK ---")
    if n_black == 0:
        print("  No losses as Black in this period.")
    else:
        phase = defaultdict(int)
        piece = defaultdict(int)
        mate = defaultdict(int)
        black_scenarios: dict[tuple[str, str, str], int] = defaultdict(int)
        for r in black_losses:
            phase[r["phase_of_collapse"] or "-"] += 1
            piece[r["piece_lost_first"] or "-"] += 1
            if r["checkmating_piece"]:
                mate[r["checkmating_piece"]] += 1
            ph, pc, band = _collapse_scenario_key(r["phase_of_collapse"], r["piece_lost_first"], r["first_major_loss_move"])
            if ph != "?" or pc != "?":
                black_scenarios[(ph, pc, band)] += 1
        print(f"  Total losses as Black: {n_black}")
        for line in _reasoning_blurb(phase, piece, mate, n_black):
            print(line)
        if black_scenarios:
            top = max(black_scenarios.items(), key=lambda x: x[1])
            (ph, pc, band), cnt = top
            print(f"  Most common scenario as Black: {ph.capitalize()} + lost {_piece_name(pc)} first (moves {band}) - {cnt} games")
    print()

    # --- Section: Opening failure reasoning ---
    print("  --- OPENING FAILURE (why your openings failed) ---")
    for (color, opening), stats in sorted(opening_totals.items(), key=lambda x: (x[0][0], x[0][1])):
        total_o, wins_o, losses_o = stats
        if total_o == 0:
            continue
        key = (color, opening)
        loss_list = by_opening.get(key, [])
        loss_pct = 100 * losses_o / total_o if total_o else 0
        print(f"  [{opening}] as {color.capitalize()}: {total_o} games, {losses_o} losses ({loss_pct:.0f}% loss rate)")
        if loss_list:
            phase = defaultdict(int)
            piece = defaultdict(int)
            mate = defaultdict(int)
            for r in loss_list:
                phase[r["phase_of_collapse"] or "-"] += 1
                piece[r["piece_lost_first"] or "-"] += 1
                if r["checkmating_piece"]:
                    mate[r["checkmating_piece"]] += 1
            for line in _reasoning_blurb(phase, piece, mate, len(loss_list)):
                print(line)
        print()
    print("  -> Use this to see: London/Caro-Kann loss rate and where you collapse in each.")
    print("=" * 64)
    print()
