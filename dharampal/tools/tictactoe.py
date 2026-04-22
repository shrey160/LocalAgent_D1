"""Tic-Tac-Toe game tool.

A simple 3x3 Tic-Tac-Toe game where the user plays as X and the AI plays as O.
The board positions are numbered 1-9:

 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9

Game state persists in-memory for the current session.
After a game ends (win/lose/draw), the user can start a new game.

Usage in chat:
  User: "Let's play tic tac toe"
  User: "I pick 5"
  User: "Play tic tac toe, my move is 3"
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

# --- Game state (module-level, persists during session) ---

_game_active = False
_board = [""] * 9  # 0-8, empty string = empty
_current_player = "X"  # X = user, O = AI

_WINNING_LINES = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],  # rows
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],  # cols
    [0, 4, 8],
    [2, 4, 6],  # diagonals
]


# --- Helpers --------------------------------------------------------------


def _format_board() -> str:
    """Draw the 3x3 grid with current marks."""
    b = _board
    rows = [
        f" {b[0] or '1'} | {b[1] or '2'} | {b[2] or '3'} ",
        "---+---+---",
        f" {b[3] or '4'} | {b[4] or '5'} | {b[5] or '6'} ",
        "---+---+---",
        f" {b[6] or '7'} | {b[7] or '8'} | {b[8] or '9'} ",
    ]
    return "\n".join(rows)


def _check_winner() -> Optional[str]:
    """Return 'X', 'O', or None if no winner yet."""
    for line in _WINNING_LINES:
        a, b, c = line
        if _board[a] and _board[a] == _board[b] == _board[c]:
            return _board[a]
    return None


def _is_draw() -> bool:
    """True if board is full with no winner."""
    return all(_board) and _check_winner() is None


def _get_ai_move() -> int:
    """Simple AI: pick center if free, then corners, then random available.

    Uses board copies for testing to avoid mutating the real board.
    """
    # 1. Try to win
    for pos in range(9):
        if _board[pos] == "":
            test_board = _board.copy()
            test_board[pos] = "O"
            if _check_winner_on_board(test_board) == "O":
                return pos

    # 2. Block user from winning
    for pos in range(9):
        if _board[pos] == "":
            test_board = _board.copy()
            test_board[pos] = "X"
            if _check_winner_on_board(test_board) == "X":
                return pos

    # 3. Take center
    if _board[4] == "":
        return 4

    # 4. Take a corner
    for pos in [0, 2, 6, 8]:
        if _board[pos] == "":
            return pos

    # 5. Take any available
    for pos in range(9):
        if _board[pos] == "":
            return pos

    return -1  # board full (shouldn't happen if called correctly)


def _check_winner_on_board(board: list) -> Optional[str]:
    """Check winner on a specific board (for AI testing)."""
    for line in _WINNING_LINES:
        a, b, c = line
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _start_new_game() -> str:
    """Reset board and return welcome message."""
    global _game_active, _board, _current_player
    _game_active = True
    _board = [""] * 9
    _current_player = "X"
    return (
        "Let's play Tic-Tac-Toe!\n\n"
        "You are X, I am O. Pick a number (1-9) to place your mark.\n\n"
        + _format_board()
    )


# --- Tool -----------------------------------------------------------------


@tool
def tictactoe_tool(move: str = "") -> str:
    """Play a game of Tic-Tac-Toe with the user.

    Use this when the user wants to play tic tac toe or makes a move.

    Args:
        move: The user's move (1-9), or empty/"yes"/"again" to start a new game.
    """
    global _game_active, _board, _current_player

    print(f"[TICTACTOE] move={move!r}, active={_game_active}, board={_board}")

    # --- Start new game if not active or user explicitly wants one ---
    lower_move = move.strip().lower()
    if not _game_active or lower_move in (
        "yes",
        "again",
        "play again",
        "new game",
        "restart",
    ):
        print("[TICTACTOE] Starting new game")
        return _start_new_game()

    # --- Parse move ---
    move = move.strip()

    # If move is empty but game is active, just show the board
    if not move:
        return (
            "Game is ongoing! Your turn (X).\n\n"
            + _format_board()
            + "\n\nPick an empty square (1-9)."
        )

    # Try to extract a number 1-9
    try:
        pos = int(move)
        if not 1 <= pos <= 9:
            raise ValueError
        idx = pos - 1
    except ValueError:
        return "Please pick a number from 1 to 9.\n\n" + _format_board()

    # Validate move
    if _board[idx] != "":
        return f"Square {pos} is already taken! Pick another.\n\n" + _format_board()

    # Make user's move
    print(f"[TICTACTOE] User places X at {pos}")
    _board[idx] = "X"

    # Check if user won
    if _check_winner() == "X":
        _game_active = False
        return (
            _format_board() + "\n\n*** You win! Congratulations! ***\n"
            "Want to play again? Just say 'yes' or 'play again'."
        )

    # Check draw
    if _is_draw():
        _game_active = False
        return (
            _format_board() + "\n\n*** It's a draw! ***\n"
            "Want to play again? Just say 'yes' or 'play again'."
        )

    # AI's turn
    ai_pos = _get_ai_move()
    if ai_pos != -1:
        _board[ai_pos] = "O"
        ai_square = ai_pos + 1

        # Check if AI won
        if _check_winner() == "O":
            _game_active = False
            return (
                _format_board() + f"\n\nI place O on {ai_square}.\n"
                "*** I win! Better luck next time. ***\n"
                "Want to play again? Just say 'yes' or 'play again'."
            )

        # Check draw after AI move
        if _is_draw():
            _game_active = False
            return (
                _format_board() + f"\n\nI place O on {ai_square}.\n"
                "*** It's a draw! ***\n"
                "Want to play again? Just say 'yes' or 'play again'."
            )

        # Game continues
        return (
            _format_board() + f"\n\nI place O on {ai_square}. Your turn!\n"
            "Pick an empty square (1-9)."
        )

    # Should not reach here
    return "Something went wrong. Let's start over!"


# --- Public helper to reset game (called by agent if user says "yes") ---


def reset_tictactoe() -> str:
    """Reset and start a new game. Called by the agent when user agrees to replay."""
    return _start_new_game()
