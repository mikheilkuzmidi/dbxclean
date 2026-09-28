# Local mode

The web app can scan a local directory without a Dropbox account or API token. Set these values in `backend/.env` before starting the backend:

```env
STORAGE_MODE=local
LOCAL_ROOT=/absolute/path/to/files
```

Follow the [web app setup](docs/web-app.md) to install and start the backend and frontend. Use a directory you own. The configured local root is the boundary for scan, move, rename, and restore paths. A request outside that root is rejected.

The local scan reads files in batches, computes Dropbox-style content hashes from their contents, and stores metadata in SQLite. Exact duplicate review is available by default. Similar-image analysis is optional and reads image data for perceptual hashing and quality scoring.

A confirmed recovery move puts a reviewed file under `LOCAL_ROOT/.dbxclean-quarantine/web`. The file stays on the same disk and continues to use storage. The Recovery page restores it to its original path if that path is free. The quarantine directory is excluded from later scans. Renames also refuse to overwrite an existing path.

For the separate command line interface, install the package and run `dbxclean`. After selecting a directory there, restore its CLI quarantine with `dbxclean --restore /path/to/chosen/directory`. The CLI and web app use separate recovery records.

See [SAFETY.md](SAFETY.md) for the exact protections and the Dropbox retention limit.
