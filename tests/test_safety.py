"""
The guarantees that make this tool safe to point at real files.

Each test here corresponds to a way the previous implementation could have
destroyed data: it deleted by path with no content check, kept no copy, and
unlinked rather than moved.
"""

import shutil
from pathlib import Path

import pytest

from dropbox_sorter.safety import DuplicateGroup, Quarantine, content_hash, find_duplicates


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "a").mkdir()
    (tmp_path / "b" / "nested").mkdir(parents=True)
    (tmp_path / "a" / "one.txt").write_text("identical content here")
    (tmp_path / "b" / "two.txt").write_text("identical content here")
    (tmp_path / "b" / "nested" / "three.txt").write_text("identical content here")
    (tmp_path / "a" / "only.txt").write_text("unique file")
    # Same byte length, different contents. Matching on size alone would call
    # these duplicates and delete one.
    (tmp_path / "a" / "clash.bin").write_bytes(b"same size diff bytes A")
    (tmp_path / "b" / "clash.bin").write_bytes(b"same size diff bytes B")
    return tmp_path


def test_groups_only_byte_identical_files(tree: Path):
    groups = find_duplicates(tree)
    assert len(groups) == 1, "the two same-size files differ and must not be grouped"
    assert len(groups[0].paths) == 3


def test_same_size_different_content_is_not_a_duplicate(tree: Path):
    a = content_hash(tree / "a" / "clash.bin")
    b = content_hash(tree / "b" / "clash.bin")
    assert (tree / "a" / "clash.bin").stat().st_size == (tree / "b" / "clash.bin").stat().st_size
    assert a != b


def test_a_unique_file_is_never_in_a_group(tree: Path):
    for group in find_duplicates(tree):
        assert tree / "a" / "only.txt" not in group.paths


def test_one_copy_is_always_kept(tree: Path):
    group = find_duplicates(tree)[0]
    assert group.keeper in group.paths
    assert group.keeper not in group.removable
    assert len(group.removable) == len(group.paths) - 1


def test_keeper_choice_is_stable(tree: Path):
    first = find_duplicates(tree)[0].keeper
    second = find_duplicates(tree)[0].keeper
    assert first == second, "a second run must not choose a different survivor"


def test_quarantine_moves_rather_than_deletes(tree: Path):
    group = find_duplicates(tree)[0]
    quarantine = Quarantine(tree)
    moved = [quarantine.hold(p, digest=group.digest, keeper=group.keeper) for p in group.removable]

    assert group.keeper.exists(), "the kept copy must survive"
    for original, target in zip(group.removable, moved):
        assert not original.exists()
        assert target.exists(), "the file must still be on disk, just elsewhere"
        assert target.read_text() == "identical content here"


def test_restore_puts_everything_back(tree: Path):
    group = find_duplicates(tree)[0]
    originals = list(group.removable)
    quarantine = Quarantine(tree)
    for path in originals:
        quarantine.hold(path, digest=group.digest, keeper=group.keeper)

    assert not any(p.exists() for p in originals)
    quarantine.restore_all()
    assert all(p.exists() for p in originals), "restore must return every file"


def test_a_second_scan_ignores_quarantine(tree: Path):
    group = find_duplicates(tree)[0]
    quarantine = Quarantine(tree)
    for path in group.removable:
        quarantine.hold(path, digest=group.digest, keeper=group.keeper)

    # Only the kept copy remains in the tree proper, so nothing is duplicated.
    assert find_duplicates(tree) == []


def test_empty_files_are_left_alone(tmp_path: Path):
    (tmp_path / "x").write_text("")
    (tmp_path / "y").write_text("")
    assert find_duplicates(tmp_path) == [], "zero length files are not worth reclaiming"
