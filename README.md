# MTH 4322 Transportation System

Working folder: `/Users/youssefelfarsy/.codex/.chatgpt-projects/g-p-6aa703ad56f88191adfd4ddec6d7f944/transportation4322`

Stages 1–4 are implemented and agent-tested. The user has marked the Stage 2
and Stage 3 checks done. Stage 4 personal verification remains pending.
This is not yet a usable restocking application. The Streamlit app is a launch
check; production optimization, saving edited state, and the five-screen interface come later.

## Run

From this folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Stop the app with Ctrl-C. It opens locally; it does not arrange deliveries.

To reproduce setup on another machine with Python 3.14:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
```

The original environment was macOS 27.0.1 arm64, Python 3.14.7, Streamlit 1.67.0.
The lock file records installed versions; a clean second-machine install has not
been tested. Streamlit is the only direct third-party dependency. The data model
and its tests use Python's standard library. There is no optimization library.

## Files and responsibilities

- `app.py`: minimal Streamlit startup screen only.
- `data_model.py`: validated immutable state, dictionary/JSON conversion, quantity
  and shipping-price edits. No file writes, routing decisions, or UI dependency.
- `availability.py`: per-item supply, demand, maximum shippable units and shortages;
  no routing or cost optimization.
- `data/sample.json`: exact main-screen dataset from the approved UI, with costs
  converted to cents. Never overwrite it with working inventory.
- `tests/test_availability.py`: hand-calculated cases and 200 seeded tiny cases
  checked by unit matching.
- `tests/brute_force_reference.py`: bounded exhaustive reference for one item;
  testing only, independent of production logic.
- `tests/test_brute_force_reference.py`: manual cases, 6,561 exhaustive cases,
  200 seeded cases and failure checks.
- `tests/audit_reference.py`: second pass over 65,536 cases with a third method
  plus three deliberate in-memory defect checks.
- `tests/test_validation_boundaries.py`: regressions for all three audit findings.
- `tests/test_data_model.py`: sample, invalid-input, boundary, isolation, and
  seeded edit tests. `tests/test_app.py`: app execution and rerun check.
- `tests/smoke_server.py`: explicit two-cycle server startup/health/shutdown check;
  uses local port 18522 and requires permission to open a local socket.
- `docs/reference/`: copies of references; original sources remain untouched.
- `docs/approved-plan.md`: recovered plan, including original chat citation tokens
  that are not independently resolvable source citations.
- `docs/verification-log.md`: actual commands, results, failures, limitations.
- `docs/checklist.md`: stages, source inventory, course deliverables and dates.
- `docs/understanding-check.md`: explanation and student verification exercise.

## Data contract

Catalogs map stable IDs to display names. Inventory maps warehouse IDs to item
quantities; demand maps store IDs to missing item quantities. Shipping prices map
warehouse IDs to store IDs, independent of item type. Every required cell must
exist: a missing price never silently becomes a free route.

Quantities, prices in cents, and revisions must be nonnegative Python integers.
Booleans, floats, numeric strings, NaN and infinity are rejected. Zero is valid.
No rounding occurs. A future UI must explicitly convert money entry to cents.
Each stored integer is limited to `10**300 - 1` (300 decimal digits), including
revision. This explicit bound keeps accepted state serializable under the tested
Python JSON settings, even at Python's minimum configurable digit limit of 640.
An edit exceeding the bound fails without changing state. Computed totals are
not restricted by the per-cell bound. UI input limits will be decided and tested
when input widgets are built.

There must be at least one item, warehouse, and store. This is an explicit project
choice, not an instructor requirement. Each catalog has unique IDs; duplicate
JSON keys are rejected. Display names may repeat, and IDs are scoped to their
catalog (warehouse and store namespaces are distinct). Names cannot be blank or
have leading/trailing whitespace. Catalogs remain fixed during ordinary edits.

`State` copies and freezes nested mappings. `to_dict()` returns a detached copy.
`with_quantity()` supports set, add and remove; it rejects removing too much.
`with_shipping_cost()` sets one price in integer cents. Successful changes return
a new validated state with revision increased once; no-ops return the old state.
Failed changes leave the old state untouched. Revision alone is not a globally
unique identity: Stage 7 must also handle resets/branches and stale previews.

For n1 items, n2 warehouses and n3 stores, validation and snapshot copying cost
O(n1(n2+n3) + n2*n3) time and space, ignoring string lengths and integer bit sizes.
An edit currently copies and revalidates the whole state for clarity and safety.
Direct cell reads use dictionary lookup. Availability/shortage functions are implemented in `availability.py`.

Future optimization contract: independently for each item, maximize shipped
units, then minimize cost. Fairness and shared route capacity are outside scope.
No linear programming and no library that directly solves the required algorithm.

## Evidence and limitations

See `docs/stage4-tests.log`: 43 tests passed, including the earlier tests plus
reference and validation regression tests. The independent audit is in
`docs/stage4-independent-audit.log`; a repeat with the minimum configurable Python
integer-conversion digit limit (640) is in `docs/stage4-second-pass.log`. Expected
sample totals are 9 keyboards/5 monitors in stock and 7 keyboards/3 monitors
needed. These totals were checked directly against the PDF; the $14/$20 cost examples now also match exhaustive enumeration and
hand-worked lower bounds. The efficient production solver is not implemented.

Streamlit AppTest checks script execution, not browser appearance. Its official
documentation is https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest.
The server health probe returned HTTP 200 twice and both processes exited 0.
No server is intentionally left running. No GitHub publication or submission occurred.

AI: OpenAI Codex in the desktop app. Student understanding, personally performed
checks, and an accurate initial-design history must be recorded separately.
Do not submit these agent checks as if you personally performed them.

Stage 3 explanation and runnable personal check: `docs/stage3-understanding-check.md`.
Stage 4 explanation and runnable personal check: `docs/stage4-understanding-check.md`.
The next stage is the production minimum-cost-flow implementation, after the Stage 4 check.
