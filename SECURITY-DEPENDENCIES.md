# Dependency security maintenance

The backend requirements include the complete Python 3.12 dependency resolution, including transitive security updates. Maintain direct dependencies in `backend/requirements.in`, then regenerate `backend/requirements.txt` with:

```sh
uv pip compile --no-build --python-version 3.12 --universal backend/requirements.in --output-file backend/requirements.txt
```

Validation on 2026-10-26: 19 passed: CLI safety plus simulated Dropbox pagination, local image analysis, quarantine/restore API flows. zero findings in complete 45-package universal resolution.

Source references: [uv resolution](https://docs.astral.sh/uv/pip/compile/), [OSV database](https://osv.dev/), [Pillow security releases](https://pillow.readthedocs.io/en/stable/releasenotes/).

Removed the unused `python-jose` dependency. The supported Dropbox SDK and Stone releases no longer need the vulnerable `pkg_resources`/old setuptools compatibility constraint.
