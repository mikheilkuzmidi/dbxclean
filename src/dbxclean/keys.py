"""
Raw keyboard input, so the interface is driven by pressing rather than typing.

The sibling project dbxpull asks its questions with input() prompts.
That means typing a path, typing a number, pressing enter. For a tool whose
whole job is deciding which files to remove, typing is the wrong input method:
a mistyped index deletes something you did not mean. Arrow keys and enter make
the wrong choice impossible to express.

This uses termios and tty directly rather than pulling in curses or Textual.
The dependency footprint of the sibling tool is one package, and matching that
is worth more than a widget library for a menu this small.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager

UP = "up"
DOWN = "down"
ENTER = "enter"
SPACE = "space"
QUIT = "quit"
BACK = "back"
OTHER = "other"


class NotATerminal(RuntimeError):
    """Raised when stdin cannot be put into raw mode."""


@contextmanager
def raw_mode():
    """Put the terminal into cbreak mode for the duration of the block."""
    if not sys.stdin.isatty():
        raise NotATerminal("stdin is not a terminal")

    import termios
    import tty

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        # Restore on the way out whatever happened, otherwise the shell is left
        # without echo and the user has to run `reset` blind.
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def read_key() -> str:
    """Block for one keypress and return one of the constants above."""
    ch = sys.stdin.read(1)

    if ch == "\x1b":
        # An escape sequence, or a bare Escape. Arrow keys arrive as ESC [ A.
        nxt = sys.stdin.read(1)
        if nxt != "[":
            return BACK
        code = sys.stdin.read(1)
        return {"A": UP, "B": DOWN}.get(code, OTHER)

    if ch in ("\r", "\n"):
        return ENTER
    if ch == " ":
        return SPACE
    if ch in ("q", "Q", "\x03"):  # q or ctrl-c
        return QUIT
    if ch in ("k", "K"):
        return UP
    if ch in ("j", "J"):
        return DOWN
    return OTHER
