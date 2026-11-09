# Verification log

Date: 2026-11-08 (America/New_York). Checks below were performed by Codex,
not by the student unless explicitly attributed. Stage 2 was subsequently confirmed
by the user below; their Stage 3 and Stage 4 exercises are also marked done.
The user subsequently reported verifying Stages 5–6. Stages 7–8 personal
explanations remain separate from agent verification.

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


## Stage 4 — 2026-11-08

User authorized fixes plus Stage 4 and requested exhaustive verification and a
second check. Student-edited Stage 2/3 verification documents remain unchanged.

Implementation: tests/brute_force_reference.py enumerates route quantities for
ONE item. Objective is lexicographic (-units, cost). It uses no production helper,
flow algorithm, or external optimizer. Inputs are copied; returned matrix is
immutable. Budget exhaustion raises SearchLimitExceeded and returns no optimum.
Limits: 1–3 warehouses/stores, 0–20 units per quantity cell, default 250,000 nodes.
These bounds keep a deliberately exponential testing tool from running indefinitely.

Observed commands and outcomes on the final code:

1. `.venv/bin/python -B -m unittest discover -s tests -v > docs/stage4-tests.log 2>&1`
   — exit 0, **43 tests passed**. Includes 6,561 exhaustive 2x2 cases with quantities
   and prices 0–2 against per-unit assignments, 200 seeded rectangular reference
   cases (seed 4324), all previous tests, and validation regressions.
2. `.venv/bin/python -B tests/audit_reference.py > docs/stage4-independent-audit.log 2>&1`
   — exit 0, **65,536 exhaustive 2x2 cases** with quantities and prices 0–3 matched
   a flat-matrix enumeration. The two exhaustive domains overlap. All three
   deliberately broken in-memory variants were detected by assertion failures:
   wrong objective priority, omitted maximum route quantity, wrong store price.
3. `PYTHONINTMAXSTRDIGITS=640 .venv/bin/python -B -m unittest discover -s tests -v > docs/stage4-second-pass.log 2>&1`
   — exit 0, **43 tests passed again** under the minimum configurable digit limit.
   This environment setting affected only that process, not the global setup.
4. Direct example execution: keyboards (7 units,1000 cents), original monitors
   (3,400), partial monitors (5,1000), greedy counterexample (2,400). Allocations
   matched the original PDF examples and the hand-derived lower bounds documented
   in stage4-understanding-check.md.
5. A 3x3 input with every stock/demand cell equal to 20 hit the default search
   budget and raised SearchLimitExceeded. Added this case to the permanent tests,
   then reran both the full suite and independent audit on the final code.

Double-check review: every feasible matrix has one route-choice sequence;
capacity deductions prevent infeasible leaves; restoration isolates sibling
branches; negative units sorts maximum fulfillment first; price is secondary;
zero/tied-cost paths are included. Search-limit exceptions cannot return a partial
best candidate. Independent checks validate both objective and returned feasibility.
No test failures required an algorithm correction in this implementation session.

Limits of evidence: exhaustive only over the stated finite domains; random checks
cover additional rectangular cases, not every supported input. No production
optimizer, persistent storage, or full interface yet. Student Stage 4 understanding
remains pending. Stage 5 has not started. No publication or submission occurred.


## Stage 5 — 2026-11-08

User marked the Stage 4 exercise done and requested the next stage. Implemented
optimizer.py with successive shortest augmenting paths and Bellman–Ford, reverse
capacities/negative costs, full bottleneck augmentation, immutable plan output,
projected stock/demand, and exact source snapshot. No persistence or UI mutation.

Final pre-Stage-6 command: `.venv/bin/python -B -m unittest discover -s tests -v > docs/stage5-tests.log 2>&1`:
exit 0, **57 tests passed**. Includes 6,561 exhaustive cases, 400 seeded multi-item
rectangular cases (seed 4325), 30 larger price-shift/more-stock checks, all prior tests.
`.venv/bin/python -B tests/audit_optimizer.py > docs/stage5-independent-audit.log 2>&1`:
exit 0; **65,536** exhaustive 2x2 cases match flat enumeration; 200 larger cases
(seed 54325) pass an independently reconstructed residual-cycle certificate using
Floyd–Warshall. Certificate rejects the known greedy allocation. Three deliberate
in-memory defects were detected: disabled reverse capacity (assertion failure),
wrong reverse sign (error), and wrong route price (assertion failure and errors).

Executed original and partial examples: 10 units/1400 cents and 12 units/2000 cents;
partial remaining demand is 2 monitors at Store Y. Source State remained unchanged.
Double-check review covered reverse-index pairing, capacity restoration, strict
relaxation with zero/tied prices, integer-only distances, and final route-cost
reconciliation. No test failure required a solver correction in this stage.

The user then explicitly authorized completing Stage 5 and implementing Stage 6
in this session. Stage 5 agent gate passed; personal explanation remains separate.


## Stage 6 — 2026-11-08

Resumed by inspecting git status, Stage 5 implementation and its passing logs.
Stage 5 checkpoint: f58bec0. User explicitly requested completing both stages.

Added heap Dijkstra with vertex potentials, full reachable search before potential
updates, and a guard against negative reachable reduced costs. Bellman–Ford remains
selectable. Default method is Dijkstra. Both sum original path costs and reconcile
final route costs. Exact input State retained; no confirmation/persistence added.

Commands and observed results on the final code:

- `.venv/bin/python -B -m unittest discover -s tests -v > docs/stage6-tests.log 2>&1`:
  exit 0, **63 tests passed**. Includes 6,561 exhaustive cases comparing BOTH methods
  to the Stage 4 oracle, plus all previous tests and six potential-specific tests.
- `.venv/bin/python -B tests/audit_stage6.py > docs/stage6-independent-audit.log 2>&1`:
  exit 0. Both methods match flat enumeration on **65,536** exhaustive 2x2 cases,
  quantities/prices 0–3. 300 seeded multi-item cases match Stage 4; 150 larger
  multi-item cases have equal objectives and independently certified residual
  graphs (seed 4326). These finite domains overlap earlier tests.
- Deliberately omitting potential updates, reversing potential signs, and charging
  reduced distances as currency were all rejected by runtime checks (three errors
  per defective variant). Real source files were not modified by these checks.
- `PYTHONINTMAXSTRDIGITS=640 .venv/bin/python -B -m unittest discover -s tests -v > docs/stage6-second-pass.log 2>&1`:
  exit 0, **63 tests passed again**.
- `.venv/bin/python -B tests/audit_optimizer.py > docs/stage6-regression-audit.log 2>&1`:
  exit 0; Stage 5 exhaustive/certificate/mutation audit also passes with the new
  default Dijkstra implementation.
- `.venv/bin/python -B tests/audit_reference.py > docs/stage6-reference-regression.log 2>&1`:
  exit 0; independent Stage 4 reference audit still passes.

Paired benchmark (seed 64322), Python 3.14.7 arm64 Darwin, warmed methods, alternating
order, median of three runs per fixed instance; each result validated:

| Warehouses × stores × items | Bellman–Ford seconds | Dijkstra seconds | Ratio |
|---|---:|---:|---:|
| 4 × 4 × 2 | 0.000179 | 0.000140 | 1.28 |
| 12 × 12 × 3 | 0.004416 | 0.002451 | 1.80 |
| 30 × 30 × 3 | 0.072483 | 0.030051 | 2.41 |
| 60 × 60 × 3 | 0.694003 | 0.202872 | 3.42 |

Double-check review: initial nonnegative active costs justify zero potentials;
shortest-distance inequalities preserve nonnegative reachable reduced costs;
newly enabled reverse path edges have zero reduced cost; unreachable vertices
are not assigned tentative potentials. Heap stale entries are skipped. Currency
uses original costs, and tied allocation differences are accepted if objective
and feasibility agree. The invariant guard never fired on any valid test input.

No solver correction was needed after test execution; all deliberately broken
variants are isolated test experiments. No new dependency or external solver was
introduced. All original reference files and student-edited verification documents
remain unchanged. Agent implementation gates for Stages 5 and 6 are complete.
Student understanding is not inferred from those results. Stage 7 has not started.
No browser changes, live delivery, persistence, publication or submission occurred.


## Stage 7 — 2026-11-08

User reported reviewing/verifying Stages 5–6 and explicitly authorized Stages 7–8.
Added independent plan validation, pure candidate application, and RestockSession
with identity-bound active previews. All edits/reset invalidate active previews
except no-ops/failed edits. Full source equality prevents same-revision branches.
No zero-shipment confirmation. Revision increments once per successful transition.

`.venv/bin/python -B -m unittest discover -s tests -v > docs/stage7-tests.log 2>&1`:
exit 0; **72 tests passed**, including 9 new operation tests. Finite exhaustive
coverage: 81 tiny capacity configurations with both solvers, and 2,401 action
sequences of length four over seven actions, checked step-by-step against a
separate scalar model. Tests also cover stale/canceled/replaced/foreign handles,
repeat confirmation, partial fulfillment then replenishment, malformed plan fields,
boolean projections, price/stock/demand changes, no-ops, and revision overflow.

Reviewed transition ordering before proceeding: all validation/candidate building
occurs before session state mutation; confirmation clears the handle only after
commit; original sample remains unchanged. Stage 7 in-memory gate passed. Stage 8
will insert the persistent commit before publishing the candidate in memory.


## Stage 8 — 2026-11-08

Added JsonStore and store-backed RestockSession.open/reload/commit. Snapshot checks
compare full validated states. Writes stage JSON in the same directory, flush and
fsync the file, then atomically replace the current save. Initial creation uses an
atomic no-clobber hard link. Memory updates and preview retirement follow success.
Reset keeps the current revision sequence; sample/reference targets are protected.

Final commands and observed outcomes:

- `.venv/bin/python -B -m unittest discover -s tests -v > docs/stage8-tests.log 2>&1`:
  exit 0; **88 tests passed**. Includes 2,401 four-action in-memory traces, malformed
  plan fields, all prior algorithm tests, 15 storage tests, same-revision conflicts,
  actual fresh-process reload, Unicode/large-number round trips and failure cases.
- `.venv/bin/python -B tests/audit_transactions.py > docs/stage8-independent-audit.log 2>&1`:
  exit 0; all **512** length-three persistent traces over eight actions matched a
  separate scalar model at every step, on disk and in memory. Real child processes
  exited immediately before replacement (exit 23: complete old state recovered)
  and after replacement (exit 24: complete new state recovered). Orphan staging
  files were ignored. Three in-memory defect variants were caught by assertion
  failures: missing active-handle checks, missing source checks, skipped disk commit.
- `PYTHONINTMAXSTRDIGITS=640 .venv/bin/python -B -m unittest discover -s tests -v > docs/stage8-second-pass.log 2>&1`:
  exit 0; **88 tests passed again** under the stricter numeric-conversion setting.
- `.venv/bin/python -B tests/audit_stage6.py > docs/stage8-optimizer-regression.log 2>&1`:
  exit 0; both solvers still match 65,536 exhaustive cases, 300 small multi-item
  cases and 150 larger certified cases. Existing defect checks and benchmark reran.

Fault checks: temporary-file creation, partial write, flush, fsync, replace,
cleanup, corrupted/missing file, stale second session, invalid revision/catalog,
reset/edit failure, and interruption after successful publication but before
acknowledgment. Before-publication failures preserve original bytes and memory.
After-publication interruption may leave memory old and disk new: repeated stale
confirmation is rejected, and reload reconciles the state without a second deduction.

Critique-driven additions: explicit test that validate_plan checks feasibility,
not global optimality; forged preview handles cannot inject a different plan.
Added revision-only stale snapshot regression and failed-edit/reset persistence
checks, not just confirmation failures. The initial failure-injection tests passed; the later path-validation regression
and correction are recorded below. Expected injected failures are not data-loss events.

Ran the documented temporary-file demonstration: preview 12 units/2000 cents;
reopened demand 2 monitors; replenished B and previewed 2 units/200 cents; final
outstanding monitors 0. Output in stage8-demo.log. Then explicitly initialized
`data/current_state.json` from the original sample (revision 0). That file is
ignored by Git, remains separate from sample.json, and was reloaded successfully.

Stage 7 checkpoint: 73159ec. Stage 8 agent gate passed. Personal verification
remains for the student. All original PDFs and student-edited understanding files
are preserved. The UI is still the setup screen; Stage 9 has not started.

Limits: finite exhaustive domains only; one local user, no simultaneous-writer
locking. No parent-directory fsync, so sudden power-loss or network-filesystem
persistence is not guaranteed. No backups, corruption auto-repair, publication,
submission, or real deliveries were performed.


Final Stage 8 path review added a regression for a looping parent symlink. The
first rerun FAILED (1 failure in 88 tests): non-strict Path.resolve left the loop
unresolved, so JsonStore construction did not raise StorageError as expected.
The prior audit/second-pass logs at that point were from before this final change;
they were not fresh passing evidence. Failed output is preserved separately in
stage8-path-regression-failure.log. An interim commit preceded inspection of that
failure; it is superseded by the correction checkpoint, not treated as acceptance.

Corrected _check_target to resolve the already-required parent strictly and check
that it is a directory. After inspecting the correction, reran the complete suite,
persistent action/process/mutation audit, and numeric-limit second pass. Observed
exit 0 for the full command chain; **88 tests passed in each full run**, all 512
persistent traces passed, both real process-interruption checks passed, and all
three deliberate defects were detected. Final acceptance is based on these fresh
logs. No further runtime source changes followed those runs.
