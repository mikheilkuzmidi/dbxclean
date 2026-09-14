"""
Entry point for the sorter.

Dry run is not a flag you remember to pass. It is what the tool does unless you
walk through the interface and confirm otherwise, and even then the answer is
"move into quarantine", never "delete".
"""

from __future__ import annotations

import sys
from pathlib import Path

from dropbox_sorter import keys, tui
from dropbox_sorter.safety import Quarantine, find_duplicates

USAGE = """dropbox-sorter - find duplicate files and set them aside safely

Usage:
  dropbox-sorter            Start the interface, choose a directory, review
  dropbox-sorter --help     Show this message
  dropbox-sorter --restore  Put everything back out of quarantine

Nothing is ever deleted. Duplicates you select are moved into a quarantine
directory beside the files, and every move is logged so it can be undone. One
copy of every group is always kept.
"""


def run_restore() -> int:
    root = Path.cwd()
    quarantine = Quarantine(root)
    restored = quarantine.restore_all()
    if not restored:
        print("Nothing in quarantine to restore.")
        return 0
    for src, dst in restored:
        print(f"restored {dst}")
    print(f"\n{len(restored)} files restored.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if any(a in ("-h", "--help") for a in args):
        print(USAGE)
        return 0
    if "--restore" in args:
        return run_restore()

    try:
        with keys.raw_mode():
            root = tui.pick_directory(Path.cwd())
            if root is None:
                tui.clear()
                print("Nothing scanned.")
                return 0

            tui.clear()
            tui.banner(f"Scanning {root}")
            print("  Hashing files. Only files of equal size are hashed.\n")
            groups = find_duplicates(root)

            if not groups:
                tui.clear()
                tui.banner("No duplicates found")
                print(f"  Nothing under {root} has a byte-identical twin.\n")
                return 0

            selected = tui.review_groups(groups, root)
            if not selected:
                tui.clear()
                print("Nothing selected. No files were touched.")
                return 0

            chosen = [groups[i] for i in sorted(selected)]
            count = sum(len(g.removable) for g in chosen)
            size = sum(g.reclaimable_bytes for g in chosen)

            if not tui.confirm(count, size):
                tui.clear()
                print("Cancelled. No files were touched.")
                return 0

            quarantine = Quarantine(root)
            moved = 0
            for group in chosen:
                keeper = group.keeper
                for path in group.removable:
                    quarantine.hold(path, digest=group.digest, keeper=keeper)
                    moved += 1

            tui.clear()
            tui.banner("Done")
            print(f"  {moved} files moved into {quarantine.dir}")
            print(f"  One copy of every group was kept.")
            print(f"  Log: {quarantine.oplog}")
            print(f"\n  Undo all of it with: dropbox-sorter --restore\n")
            return 0

    except keys.NotATerminal:
        # Piped, redirected, or running under CI. A menu cannot be driven there,
        # and a stack trace would make this look like a crash.
        print(
            "dropbox-sorter is an interactive tool and needs a terminal.\n"
            "Run it directly rather than through a pipe or redirect, "
            "or use --help to see what it does.",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        tui.clear()
        print("Interrupted. No files were touched.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
