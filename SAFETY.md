# Safety

This tool exists to remove duplicate files, so the only thing that really
matters is that it cannot remove the wrong ones.

## What it will not do

**It never deletes.** There is no call to `os.remove`, `unlink` or
`files_delete_v2` anywhere in the sorter. Files you select are moved into a
`.dbxclean-quarantine` directory beside them. They are still on disk,
still readable, and still yours.

**It never removes the last copy.** A duplicate group always keeps one member.
The survivor is chosen deterministically, by shallowest path, then oldest, then
alphabetical, so a second run makes the same choice rather than a new one.

**It never acts without being told to.** Starting the tool scans and shows you
what it found. Nothing moves until you select groups and then confirm a prompt
that names how many files are affected and defaults to no.

**It never guesses what a duplicate is.** Files are grouped by SHA-256 of their
contents. Size is compared first only because it is free, and files that agree
on size but differ in bytes are not grouped. Matching on name or size alone
would call two unrelated files identical, and the cost of that mistake here is
somebody's file.

## Undo

Every move is appended to `.dbxclean-quarantine/operations.jsonl` with the
original path, the new path, the content hash and which copy was kept. To put
everything back:

    dbxclean --restore

## What changed

The web API in `backend/` deletes for real: local storage calls `os.remove` and
Dropbox storage calls `files_delete_v2`, both immediately and irreversibly.
Nothing in that path checks whether the file being removed is the last surviving
copy of its contents, so passing every path in a duplicate group would have
removed all of them. That code is untouched and still present, but it is not
what the `dbxclean` command runs.
