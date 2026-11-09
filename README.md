# MTH 4322 Transportation System

A local Python + Streamlit application for warehouse inventory, store demand,
and minimum-cost restocking. It calculates shipment instructions; it does not
book deliveries. Run the commands below from this project folder. No personal
computer path is required.

## Set up and run

Tested with Python 3.14.7 and Streamlit 1.67.0 on macOS arm64. A fresh virtual
environment and a separate project copy were tested on the same computer;
other operating systems have not been verified.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip check
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -m streamlit run app.py --server.address=127.0.0.1
```

Open the local URL printed in the terminal. Stop with Ctrl-C. On Windows, virtual
environment executables are under `.venv\Scripts\` instead of `.venv/bin/`;
that platform has not been tested.

On first use, choose **Create sample workspace**. Working data is saved in
`data/current_state.json`, separate from the protected `data/sample.json`.
Existing invalid data is reported rather than silently overwritten.

## Edit and restock

1. Double-click a quantity or price cell. Finish each cell with Enter or Tab,
   check that the grid shows the intended value, and continue editing other cells.
2. **Save all changes** validates all three tables and saves the batch once.
   One invalid value rejects the whole batch. **Discard table edits** restores
   saved values. Unsaved browser drafts do not survive page reloads.
3. For a single adjustment, expand **Add, set or remove one quantity**. Choose
   warehouse stock or store demand, item, operation and quantity, then **Save
   quantity**. Save or discard table edits before using this shortcut.
4. **Preview restock** calculates from saved values. Unsaved table changes must
   first be saved or discarded. Preview and Cancel do not modify inventory.
5. Review shipments, cost, projected stock and remaining demand. **Confirm
   restock** or **Approve partial restock** saves the change exactly once.
   Confirmation is disabled when no units can ship.

Quantities use whole nonnegative numbers. Prices use dollars with at most two
decimal places, such as `2`, `2.5` or `2.50`; no currency symbols, commas or
rounding. Text entry preserves exact integers and cents, including values beyond
JavaScript's safe integer range. Each stored integer is limited to 300 decimal
digits. Counts in the tables are final totals, not increments.

A grid edits one active cell at a time, but **one Save can commit many edited
cells across all tables**. Batch saving prevents a half-updated scenario becoming
visible to the optimizer. The original one-cell Python methods remain useful for
Add/Set/Remove; they do not limit the batch interface.

**Saved data and reset** contains Reload and an explicitly confirmed sample
reset. Reload discards drafts and previews. After a save error, changes pause
until reload succeeds; a save may have completed before its acknowledgment was
lost. Never repeat an old confirmation to recover.

For an isolated demo, set `TRANSPORTATION_STATE_PATH` to a separate `.json` file
in an existing directory before starting Streamlit. The default path is resolved
relative to the program, not to the terminal's current directory.

## Algorithm and scope

For each item independently, ship `min(total stock, total demand)` units, then
minimize shipping cost. The handwritten successive-shortest-path solver uses
Dijkstra with vertex potentials and residual reverse edges. Bellman–Ford remains
available as a checked baseline. No linear programming or external optimization
library is used. Streamlit and its dependencies provide the interface only.

The original sample ships **10 units for $14.00**. Changing Store Y's monitor
demand from 2 to 6 ships **12 units for $20.00**, leaving 2 monitors outstanding.
Outstanding demand survives restarts. Fairness, shared vehicle capacity,
changing catalogs, concurrent writers and real delivery booking are outside scope.

## Main files

| File | Responsibility |
|---|---|
| `app.py` | Five UI states, forms and action handling |
| `ui_model.py` | Exact text/number conversion and table labels |
| `data_model.py` | Validated immutable state and individual edits |
| `availability.py` | Per-item stock, demand and shortages |
| `optimizer.py` | Pure planning with two handwritten solvers |
| `operations.py` | Batch edits, preview/cancel/confirm, reload/reset |
| `storage.py` | Validated JSON loading and atomic save replacement |
| `tests/` | Unit/workflow tests, independent references and audits |
| `docs/reference/` | Preserved assignment, course rules and initial design |

## Verification and presentation

Stages 1–9 are implemented. Stage 10 technical validation and presentation
preparation are recorded in [the final verification report](docs/stage9-10-verification.md).
Final evidence includes **113 passing tests**, a separate fresh-environment run,
a strict integer-limit repeat, exhaustive small cases, random cases, process
interruption tests, browser workflows and screenshots. Exhaustive means the
specified finite domains, not every possible input or browser interaction.

Additional repeatable checks:

```sh
.venv/bin/python -B tests/audit_stage6.py
.venv/bin/python -B tests/audit_transactions.py
PYTHONINTMAXSTRDIGITS=640 .venv/bin/python -B -m unittest discover -s tests -v
```

See [demonstration and explanation guide](docs/presentation-guide.md),
[screenshots](docs/screenshots/README.md), [verification history](docs/verification-log.md),
[course checklist](docs/checklist.md), and [AI-use record](docs/ai-use-record.md).
The student's own checks, understanding, full chat export and actual submission
remain separate requirements; agent test results do not establish those.

## Limitations

Local, single-user use only. Snapshot comparisons catch sequential stale saves,
but are not multi-process locking. Same-directory file replacement and file
`fsync` protect complete local writes; power-loss durability of directory entries
and network filesystems are not promised. There is no automatic backup or
corruption repair. Keep a separate backup of working data when needed.

The browser grid must finish a cell edit before saving; check the displayed
value after Enter/Tab. Very fast automated typing/submit sequences were observed
to miss the final uncommitted cell. Keyboard cell completion and subsequent
batch saving were verified. No claim is made for clipboard block paste,
screen-reader certification, mobile browsers or cross-browser coverage.

Original references, historical logs and student edits are retained. Historical
logs are organized under `docs/evidence/`; new local test logs are ignored.
The stage history and evidence may contain local machine paths; keep this
repository private unless those materials have been reviewed for public release.
Assignment submission has not been performed.
