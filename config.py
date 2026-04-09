"""Configuration for chess games analysis."""
import os

# Chess.com username to analyze
USERNAME = os.environ.get("CHESS_USERNAME", "12iyad")

# SQLite database path
DB_PATH = os.environ.get("CHESS_DB", "chess_analysis.db")

# API
API_BASE = "https://api.chess.com/pub"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Only analyze games from this year (None = all years)
YEAR_FILTER = 2026

# Game phase boundaries (full move number)
OPENING_END_MOVE = 10
# Endgame: no queens on board (we detect per position)
