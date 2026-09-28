# dbxclean web app

The web app scans Dropbox metadata or a local directory, shows exact duplicate groups, and lets you move reviewed files into recovery. Similar-image analysis is optional. The frontend is React and the backend is FastAPI with a SQLite cache.

## Start in local mode without Dropbox credentials

Use Python 3.10 or newer and Node.js 18 or newer. In the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

Create `backend/.env` with a disposable directory you own:

```env
STORAGE_MODE=local
LOCAL_ROOT=/absolute/path/to/files
DATABASE_URL=sqlite:///./dbxclean.db
```

Start the backend and frontend in separate terminals:

```bash
. .venv/bin/activate
cd backend
python -m app.main
```

```bash
cd frontend
npm run dev
```

Open the URL printed by Vite, usually `http://localhost:3000`. Set `LOCAL_ROOT` before starting the backend. Local mode requires an explicit directory.

## Dropbox mode

Create a Dropbox app with `files.metadata.read`, `files.content.read`, and `files.content.write` permissions. Set `STORAGE_MODE=dropbox` and `DROPBOX_ACCESS_TOKEN` in `backend/.env`, then restart the backend. Do not commit a token. The current web configuration uses an access token. It does not implement automatic refresh-token renewal.

The default scan follows Dropbox metadata pages and groups exact duplicates by Dropbox content hash. It does not download file contents. Turn on similar-image analysis to read images or thumbnails for perceptual comparison. Local mode reads file contents to hash them. Duplicate results load 100 groups at a time in the browser.

## Review and recovery

On the Dashboard, start a scan and wait until the job completes. Review the Duplicates or Similar Images page. A recommended file in each group is protected. Select at most 100 other files and confirm the move. The server checks the selection and current metadata before doing anything. Unknown, changed, and protected files are rejected.

The Recovery page lists moved files and can restore them to their original paths. In local mode, files stay in `.dbxclean-quarantine/web` and continue to use disk space. In Dropbox mode, files go to Dropbox Deleted files and can be restored only within the [account's retention period](https://help.dropbox.com/account-settings/data-retention-policy). Restoration refuses to replace an existing file. A failure is shown for each path.

The All Files page offers naming suggestions. A rename is checked against the scan, and an existing destination is never overwritten.

## API and verification

Relevant routes are `POST /api/scan`, `GET /api/jobs/{id}`, `GET /api/duplicates?limit=100&offset=0`, `GET /api/similar`, `POST /api/trash`, `GET /api/recovery`, `POST /api/restore`, and `POST /api/rename`. `POST /api/delete` is a compatibility alias for `/api/trash`; it does not perform an irreversible local delete. Move, restore, and rename requests require `confirm=true`.

Run `./verify.sh` from the repository root after installing the Python and frontend dependencies. The tests use disposable files and a simulated Dropbox client. A separate 700,000-entry metadata scan is available with `PYTHONPATH=src python -m backend.tests.large_scan_check`. No live Dropbox-account result is claimed by these checks.
