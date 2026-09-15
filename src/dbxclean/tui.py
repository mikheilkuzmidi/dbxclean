"""
The interface. Arrow keys and enter, nothing typed in.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dbxclean import keys
from dbxclean.safety import DuplicateGroup, Quarantine, find_duplicates

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"


def human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def clear() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def banner(subtitle: str) -> None:
    print(f"{BOLD}  DBXCLEAN{RESET}")
    print(f"  {DIM}{subtitle}{RESET}\n")


def menu(title: str, options: list[tuple[str, str]], *, footer: str = "") -> int | None:
    """
    Show a list and return the chosen index, or None if the user backed out.

    options is a list of (label, hint) pairs.
    """
    index = 0
    while True:
        clear()
        banner(title)
        for i, (label, hint) in enumerate(options):
            marker = f"{CYAN}>{RESET}" if i == index else " "
            style = BOLD if i == index else ""
            print(f"  {marker} {style}{label}{RESET}")
            if hint:
                print(f"      {DIM}{hint}{RESET}")
        print()
        print(f"  {DIM}up and down to move, enter to choose, q to quit{RESET}")
        if footer:
            print(f"  {DIM}{footer}{RESET}")

        key = keys.read_key()
        if key == keys.UP:
            index = (index - 1) % len(options)
        elif key == keys.DOWN:
            index = (index + 1) % len(options)
        elif key == keys.ENTER:
            return index
        elif key in (keys.QUIT, keys.BACK):
            return None


def review_groups(groups: list[DuplicateGroup], root: Path) -> set[int]:
    """
    Walk the duplicate groups and let the user mark which to act on.

    Nothing is selected to begin with. Acting on files is an explicit choice,
    made group by group, rather than something you opt out of.
    """
    selected: set[int] = set()
    index = 0
    while True:
        clear()
        total = sum(groups[i].reclaimable_bytes for i in selected)
        banner(f"{len(groups)} duplicate groups found, {len(selected)} selected, {human(total)} reclaimable")

        window = groups[max(0, index - 4) : index + 5]
        offset = max(0, index - 4)
        for i, group in enumerate(window, start=offset):
            marker = f"{CYAN}>{RESET}" if i == index else " "
            box = f"{GREEN}[x]{RESET}" if i in selected else "[ ]"
            keeper = group.keeper.relative_to(root)
            print(f"  {marker} {box} {len(group.paths)} copies, {human(group.reclaimable_bytes)} reclaimable")
            print(f"        {GREEN}keep{RESET}  {keeper}")
            for path in group.removable[:3]:
                print(f"        {YELLOW}move{RESET}  {path.relative_to(root)}")
            if len(group.removable) > 3:
                print(f"        {DIM}      and {len(group.removable) - 3} more{RESET}")
            print()

        print(f"  {DIM}up and down to move, space to select, enter to continue, q to quit{RESET}")

        key = keys.read_key()
        if key == keys.UP:
            index = (index - 1) % len(groups)
        elif key == keys.DOWN:
            index = (index + 1) % len(groups)
        elif key == keys.SPACE:
            selected.symmetric_difference_update({index})
        elif key == keys.ENTER:
            return selected
        elif key in (keys.QUIT, keys.BACK):
            return set()


def confirm(count: int, size: int) -> bool:
    """
    The one place a destructive action is agreed to.

    It names the number of files and defaults to no, so holding enter through
    the interface cannot move anything.
    """
    choice = menu(
        f"Move {count} files into quarantine, reclaiming {human(size)}?",
        [
            ("No, leave everything where it is", "nothing is moved"),
            ("Yes, move them into quarantine", "reversible, originals are not deleted"),
        ],
    )
    return choice == 1


def pick_directory(start: Path) -> Path | None:
    """Choose a directory by walking into it, without typing a path."""
    current = start.resolve()
    while True:
        entries = sorted(
            [p for p in current.iterdir() if p.is_dir() and not p.name.startswith(".")],
            key=lambda p: p.name.lower(),
        )[:40]
        options = [(f"Use this directory: {current}", "scan here for duplicates")]
        if current.parent != current:
            options.append((".. go up", str(current.parent)))
        options.extend((f"{p.name}/", "") for p in entries)

        choice = menu("Choose a directory", options)
        if choice is None:
            return None
        if choice == 0:
            return current
        if current.parent != current and choice == 1:
            current = current.parent
            continue
        shift = 2 if current.parent != current else 1
        current = entries[choice - shift]
