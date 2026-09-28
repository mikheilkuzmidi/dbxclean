# Setup

For the browser app, follow the current [web app setup](docs/web-app.md). It covers local mode without a Dropbox token, Dropbox mode, installation, launch, review, recovery, and verification.

For the standalone local CLI, use Python 3.10 or newer:

```bash
python3 -m pip install -e .
dbxclean
```

After selecting a directory in the CLI, restore quarantined files from any working directory with:

```bash
dbxclean --restore /path/to/chosen/directory
```

The credential-free checks are described in the [README](README.md). They do not require a Dropbox app or access token.
