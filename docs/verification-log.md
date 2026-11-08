# Verification log

Date: 2026-11-08 (America/New_York). Checks below were performed by Codex,
not by the student unless explicitly attributed. Stage 2 was subsequently confirmed
by the user below; Stage 3 personal verification remains pending.

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

## Stage 2

- Read assignment p. 1, general instructions pp. 1-2, policy, syllabus, approved
  plan, and UI sample. SHA-256 checks established that the Desktop assignment
  and UI PDFs match the recovered chat attachments. Original files were not edited.
- Implemented `data_model.py`, `data/sample.json`, and `tests/test_data_model.py`.
- `.venv/bin/python -m unittest discover -s tests -v > docs/stage2-tests.log 2>&1`:
  **16 tests passed**, including 15 model tests and 1 app smoke test; 0 failures.
  The seeded test uses seed 4322 for 250 independent dictionary-checked set edits.
  Subcases cover invalid numbers, schemas, catalogs and matrix references.
- Sample independently transcribed from UI panel 01: A=(5,2), B=(4,3), X=(3,1),
  Y=(4,2), costs in cents A=(200,500), B=(400,100). Tests use literal expected
  cells and manually summed totals, not model-generated expected values.
- Inspected implementation against the contract: validation covers all required
  cells, nested mappings are copied and frozen, edits validate before returning,
  no missing route defaults, no optimizer or external algorithm library.
- Executed the example in `understanding-check.md`: original A stayed at 5/2,
  updated A became 8/2, removing 9 raised ValidationError, updated A remained 8/2.
- `.venv/bin/python -m compileall -q app.py data_model.py tests`: exit 0.
- No model test failures occurred in this run. The earlier setup failures are
  documented above; no fabricated bug-fix history is claimed.

Stage 2 agent checks passed. The student understanding/personal verification gate
remains open, so Stage 3 has not started. Empty catalogs are explicitly rejected;
zero quantities/costs and singleton catalogs are accepted. Large Python integers
were tested, but this makes no claim about future browser input limits.

Not verified: optimal plans, persistent saving/reloading, actual browser layout,
student understanding, a clean-machine reinstall, live Brightspace updates.
The original UI PDF was rendered for inspection; Poppler emitted Type 3 glyph
bounding-box warnings, but the rendered page and sample tables were readable.

Stage 1 Git checkpoint: `eb3932d`. Stage 2 is a separate subsequent commit.
No remote repository, push, or submission has been made.


## Stage 2 gate update — 2026-11-08

The user reported: “i just did the understanding verification, it makes sense and
answers match, let's move on to the next stage.” Their existing edit marks
`docs/understanding-check.md` Done. That edit was preserved unchanged. This is
user-reported verification, not a claim that Codex observed their terminal run.
Stage 2 gate is satisfied for progression to Stage 3.

## Stage 3 — 2026-11-08

- Added `availability.py`: read-only item-ID report with supply, demand, shippable
  units, and shortage. Receives validated State, performs no mutation or file I/O.
- Added `tests/test_availability.py`: 10 focused tests. Hand expectations include
  the original UI, partial UI, singleton exact/excess/shortage/zero cases, mixed
  items across locations, large integers, price independence, catalog order,
  immutable results, invalid input type, and unchanged original snapshots.
- Independent count check: 200 seeded random states (seed 4323), 1–4 items,
  warehouses and stores, quantities 0–5; a test-only unit pairing loop determines
  expected shipped and remaining units without the production min formula.
- `.venv/bin/python -m unittest discover -s tests -v > docs/stage3-tests.log 2>&1`:
  exit 0; **26 tests passed** (10 new plus 16 existing), zero failures.
  Existing AppTest emits its benign missing-ScriptRunContext warning as before.
- Executed the runnable example in `stage3-understanding-check.md`: original rows
  keyboards `9 7 7 0`, monitors `5 3 3 0`; partial rows keyboards `9 7 7 0`,
  monitors `5 7 5 2`; original Store Y monitor demand remained `2`.
- Reviewed correctness: total stock and demand are upper bounds; complete routes
  and no shared capacities permit matching until one side is exhausted. Thus the
  smaller per-item count is attainable. No per-store allocation follows from it.
- O(n1(n2+n3)) arithmetic operations, O(n1) result space; no per-unit iteration
  in production. Source data and the student's verification file were preserved.
- No new dependencies, UI changes, algorithm solver, or persistence. Server checks
  were not repeated because the app and its dependencies did not change.

Stage 3 agent verification passed; personal understanding check pending. Stage 4
has not started. Counts do not establish optimal prices or shipment assignments.


## Audit fixes — 2026-11-08

User authorized fixing the audit findings and proceeding to Stage 4 after tests.
Added explicit MAX_STATE_INTEGER = 10**300 - 1 for stored cells/revisions; sums
may exceed this per-cell bound. No Python global conversion limits were changed.
Malformed edit identifiers are checked before dictionary lookup. JSON decoding
ValueError (including UnicodeDecodeError) and recursion errors are translated to
ValidationError. ItemAvailability now validates both counts at construction.

Added six regression tests covering malformed identifiers and JSON, the maximum
accepted value, maximum+1, 5001-digit quantities, atomic add/revision overflow,
no-op at maximum revision, and invalid availability construction.

Command: `.venv/bin/python -B -m unittest discover -s tests -v > docs/validation-fixes-tests.log 2>&1`.
Observed: exit 0, **32 tests passed**, 0 failures. Reviewed changes against the three
reproduced gaps before starting Stage 4. Numeric bound is an implementation choice,
not an instructor requirement. The original student verification files remain intact.
