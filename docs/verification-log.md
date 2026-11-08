# Verification log

Date: 2026-11-08 (America/New_York). Checks below were performed by Codex,
not by the student. Student verification and understanding remain pending.

## Stage 1

- Host: Apple Silicon arm64, macOS 27.0.1; Python 3.14.7 at
  `/opt/homebrew/bin/python3`. Local `.venv` created with `python3 -m venv`.
- `python3 -m venv transportation4322/.venv`: succeeded.
- `.venv/bin/python -m pip install --no-cache-dir streamlit`: installed
  Streamlit 1.67.0 and dependencies after a network-permitted retry.
  Initial restricted attempt failed DNS resolution; this was not a package incompatibility.
- `.venv/bin/python -m unittest discover -s tests -v`: 1 test passed;
  AppTest executed and reran the minimal app, without app exceptions.
- `.venv/bin/python -m pip check`: no broken requirements found.
- `.venv/bin/python -m pip freeze > requirements-lock.txt`: captured installed versions.
- First local server attempt failed with socket PermissionError under restricted execution;
  traceback preserved in `stage1-server.log`.
- `.venv/bin/python tests/smoke_server.py` with local-server permission:
  two launches returned HTTP 200 and body `ok`; both processes stopped with exit 0.
  Output from the server itself is in `server-smoke.log`.
- `git init`: created a separate repository in this project.

Technical setup gate passed. Browser visual walkthrough and student review remain pending.
AppTest is execution evidence, not a screenshot or browser interaction test.
