# Safety

Both interfaces require a review and confirmation before they move a file. They keep a recommended copy from each reviewed exact duplicate group. The web app also protects the recommended image in a similar-image group. The server checks these rules again when it receives a request, so changing a browser checkbox or calling the API directly cannot bypass them.

## Command line interface

The CLI compares local file contents using SHA-256 after filtering by size. It chooses one copy to keep by path depth, modification time, and name. Selected extras move into `.dbxclean-quarantine` under the chosen root. The log records each original and quarantine path. Restore them with `dbxclean --restore /path/to/chosen/directory`. If the original path already exists, restore stops rather than replacing it.

## Web app

The default Dropbox scan compares provider content hashes from metadata. It does not download file contents. Local web scans hash local files. Similar-image analysis is optional and reads image data or thumbnails. A matching Dropbox content hash is the exact-duplicate signal, while perceptual similarity is a separate review and does not imply byte identity.

Before moving a selected file, the API verifies that it still belongs to a reviewed group and that its current size, revision, and content hash match the scan. It refuses unknown paths, stale files, the protected recommended copy, and a request that would take every member of a group. The check also applies to the compatibility `/api/delete` route.

In local mode, selected files move to `.dbxclean-quarantine/web` under the configured root. They still occupy disk space until the user manages that directory. The Recovery page moves them back, but never overwrites an existing destination.

In Dropbox mode, the app calls Dropbox's delete operation, which places selected files in Dropbox Deleted files. The Recovery page uses the recorded revision to request restoration. Dropbox recovery is limited by the account's [file retention period](https://help.dropbox.com/account-settings/data-retention-policy). A file may become unrecoverable after that period. The app checks that the original path is free before restoration and reports any Dropbox error.

Renames also require confirmation. The API verifies the source has not changed since the scan and rejects an existing destination.

These safeguards are covered by credential-free tests and local round trips. A live Dropbox-account operation has not been tested without user credentials.
