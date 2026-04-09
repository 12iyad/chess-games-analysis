"""Parse PGNs, detect key events, and build loss summaries."""
import io
import chess
import chess.pgn

from config import OPENING_END_MOVE
from db import (
    clear_events_for_game,
    get_all_games_for_ingest,
    get_connection,
    insert_key_event,
    insert_loss_summary,
    update_game_move_count,
    update_game_opening,
)

PIECE_SYMBOL = {
    chess.KING: "K",
    chess.QUEEN: "Q",
    chess.ROOK: "R",
    chess.BISHOP: "B",
    chess.KNIGHT: "N",
    chess.PAWN: "P",
}


def _piece_symbol(piece: chess.Piece | None) -> str | None:
    if piece is None:
        return None
    return PIECE_SYMBOL.get(piece.piece_type)


def _count_queens(board: chess.Board, color: chess.Color) -> int:
    return sum(1 for sq in chess.SQUARES if board.piece_at(sq) == chess.Piece(chess.QUEEN, color))


def _detect_opening(game: chess.pgn.Game) -> str:
    """Classify opening from first moves (London, Caro-Kann, or Other)."""
    uci_moves: list[str] = []
    board = game.board()
    for node in game.mainline():
        uci_moves.append(node.move.uci())
        if len(uci_moves) >= 12:
            break
    if len(uci_moves) < 2:
        return "Other"
    # Caro-Kann: 1.e4 c6 2.d4 d5
    if (
        len(uci_moves) >= 4
        and uci_moves[0] == "e2e4"
        and uci_moves[1] == "c7c6"
        and uci_moves[2] == "d2d4"
        and uci_moves[3] == "d7d5"
    ):
        return "Caro-Kann"
    # London: 1.d4 d5 2.Bf4 (or 2.Nf3 ... 3.Bf4)
    if uci_moves[0] == "d2d4":
        for uci in uci_moves[:10]:
            if uci in ("c1f4", "c1g5"):
                return "London"
    return "Other"


def _phase(board: chess.Board, full_move: int) -> str:
    if full_move <= OPENING_END_MOVE:
        return "opening"
    if _count_queens(board, chess.WHITE) == 0 and _count_queens(board, chess.BLACK) == 0:
        return "endgame"
    return "middlegame"


def _process_game(
    conn,
    game_id: int,
    pgn: str,
    your_color: str,
    result_for_you: str,
    white_username: str,
    black_username: str,
) -> None:
    clear_events_for_game(conn, game_id)
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:
        return
    if game is None:
        return
    opening_name = _detect_opening(game)
    board = game.board()
    me_white = your_color.lower() == "white"
    us = chess.WHITE if me_white else chess.BLACK
    them = chess.BLACK if me_white else chess.WHITE
    us_label = "white" if me_white else "black"
    them_label = "black" if me_white else "white"

    first_major_loss_move: int | None = None
    piece_lost_first: str | None = None
    phase_of_collapse: str | None = None
    checkmating_piece: str | None = None
    move_count = 0

    for node in game.mainline():
        move = node.move
        piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)
        is_white_move = piece.color == chess.WHITE
        moving_side = "white" if is_white_move else "black"
        is_castle = board.is_castling(move)

        board.push(move)
        move_count += 1
        full_move = board.fullmove_number
        phase = _phase(board, full_move)

        if is_castle:
            insert_key_event(
                conn, game_id, "castled", full_move,
                side_affected=moving_side, piece_involved="K", phase=phase,
            )

        # Capture: someone lost a piece
        if captured:
            captured_symbol = _piece_symbol(captured)
            lost_queen = captured.piece_type == chess.QUEEN
            lost_rook = captured.piece_type == chess.ROOK
            lost_by_us = captured.color == us
            if lost_by_us:
                side_affected = us_label
                side_causing = them_label
                if lost_queen:
                    insert_key_event(
                        conn, game_id, "queen_lost", full_move,
                        side_affected=side_affected, side_causing=side_causing,
                        piece_involved=captured_symbol, phase=phase,
                    )
                if lost_rook:
                    insert_key_event(
                        conn, game_id, "rook_lost", full_move,
                        side_affected=side_affected, side_causing=side_causing,
                        piece_involved=captured_symbol, phase=phase,
                    )
                if captured.piece_type != chess.PAWN and first_major_loss_move is None:
                    first_major_loss_move = full_move
                    piece_lost_first = captured_symbol
                    phase_of_collapse = phase

        if board.is_checkmate():
            checkmating_piece = _piece_symbol(piece)
            insert_key_event(
                conn, game_id, "checkmate", full_move,
                side_affected=them_label, side_causing=moving_side,
                piece_involved=checkmating_piece, phase=phase,
            )

    update_game_move_count(conn, game_id, move_count)
    update_game_opening(conn, game_id, opening_name)

    if result_for_you == "loss":
        insert_loss_summary(
            conn,
            game_id,
            first_major_loss_move=first_major_loss_move,
            piece_lost_first=piece_lost_first,
            phase_of_collapse=phase_of_collapse,
            checkmating_piece=checkmating_piece,
            your_color=your_color,
        )


def run_ingest() -> int:
    conn = get_connection()
    rows = get_all_games_for_ingest(conn)
    for row in rows:
        _process_game(
            conn,
            row["id"],
            row["pgn"],
            row["your_color"],
            row["result_for_you"],
            row["white_username"],
            row["black_username"],
        )
    conn.close()
    return len(rows)
