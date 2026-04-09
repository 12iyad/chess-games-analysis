"""Weakness report: Queen Loss Pattern (v1 focus)."""
from collections import defaultdict

from config import USERNAME
from db import get_connection, get_losses_with_queen_events


def _move_range(move: int | None) -> str:
    if move is None:
        return "-"
    if move <= 10:
        return "1-10 (opening)"
    if move <= 20:
        return "11-20"
    if move <= 30:
        return "21-30"
    if move <= 40:
        return "31-40"
    return "41+"


def run_queen_loss_report() -> None:
    conn = get_connection()
    rows = get_losses_with_queen_events(conn)
    conn.close()

    if not rows:
        print("No losses in database. Run fetch + ingest first.")
        return

    total_losses = len(rows)
    losses_with_queen = [r for r in rows if r["queen_lost_move"] is not None]
    count_queen_lost = len(losses_with_queen)
    pct = (100.0 * count_queen_lost / total_losses) if total_losses else 0

    # Move distribution when queen was lost
    move_buckets: dict[str, int] = defaultdict(int)
    phase_buckets: dict[str, int] = defaultdict(int)
    for r in losses_with_queen:
        move_buckets[_move_range(r["queen_lost_move"])] += 1
        phase_buckets[r["queen_lost_phase"] or "-"] += 1

    # First major loss (when things started going wrong) for all losses
    first_loss_phase: dict[str, int] = defaultdict(int)
    piece_lost_first: dict[str, int] = defaultdict(int)
    checkmating_piece: dict[str, int] = defaultdict(int)
    for r in rows:
        first_loss_phase[r["phase_of_collapse"] or "-"] += 1
        piece_lost_first[r["piece_lost_first"] or "-"] += 1
        if r["checkmating_piece"]:
            checkmating_piece[r["checkmating_piece"]] += 1

    # --- Print report ---
    print()
    print("=" * 60)
    print("  QUEEN LOSS WEAKNESS REPORT (v1)")
    print("  Focus: when and how often you lose your queen in losses")
    print("=" * 60)
    print(f"  Player: {USERNAME}")
    print(f"  Total losses analyzed: {total_losses}")
    print()
    print("  --- Queen in losses ---")
    print(f"  In {count_queen_lost} of {total_losses} losses you lost your queen ({pct:.0f}%).")
    if count_queen_lost:
        print("  When you lost your queen (move range):")
        for bucket in ["1-10 (opening)", "11-20", "21-30", "31-40", "41+"]:
            n = move_buckets.get(bucket, 0)
            if n:
                print(f"    {bucket}: {n} games")
        print("  Phase when you lost your queen:")
        for phase in ["opening", "middlegame", "endgame"]:
            n = phase_buckets.get(phase, 0)
            if n:
                print(f"    {phase}: {n} games")
    print()
    print("  --- First major piece lost (all losses) ---")
    for piece in ["Q", "R", "B", "N", "-"]:
        n = piece_lost_first.get(piece, 0)
        if n:
            print(f"    First piece lost = {piece}: {n} games")
    print()
    print("  --- Phase where collapse started ---")
    for phase in ["opening", "middlegame", "endgame", "-"]:
        n = first_loss_phase.get(phase, 0)
        if n:
            print(f"    {phase}: {n} games")
    print()
    if checkmating_piece:
        print("  --- What checkmated you ---")
        for piece, n in sorted(checkmating_piece.items(), key=lambda x: -x[1]):
            print(f"    {piece}: {n} games")
    print()
    print("  -> Training hint: if queen loss is high in opening/early middlegame,")
    print("    focus on queen safety and early tactics (pins, forks) in your prep.")
    print("=" * 60)
    print()
