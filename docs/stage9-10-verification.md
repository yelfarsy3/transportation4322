# Stages 9–10 verification report

Agent verification, 2026-11-09. Stage 9 implementation checkpoint: `42d0e2e`.
Original references and student changes were preserved. Cleanup remains deferred.

## Observed results

Commands below ran from the project folder unless noted. All exited successfully.

| Check | Command / procedure | Result | Evidence |
|---|---|---|---|
| Final complete suite | `.venv/bin/python -B -m unittest discover -s tests -v` | 113 passed, 4.718 s | `stage9-final-tests.log` |
| Strict conversion repeat | `PYTHONINTMAXSTRDIGITS=640 .venv/bin/python -B -m unittest discover -s tests -v` | 113 passed, 5.040 s | `stage10-second-pass.log` |
| Independent optimizer audit | `.venv/bin/python -B tests/audit_stage6.py` | 65,536 exhaustive 2x2 cases, 300 seeded small multi-item cases, 150 larger certified cases; both methods agree | `stage10-optimizer-audit.log` |
| Persistence audit | `.venv/bin/python -B tests/audit_transactions.py` | 512 action traces; actual exits before/after replacement recover complete old/new state; three deliberate defects caught | `stage10-transactions-audit.log` |
| Fresh installation | New venv; `python -m pip install -r requirements-lock.txt`; `python -m pip check` | Installed locked dependencies; no broken requirements | `stage10-fresh-install.log` |
| Fresh project suite | New venv's `python -B -m unittest discover -s tests -v` | 113 passed, 7.690 s; includes full/partial application workflows | `stage10-fresh-tests.log` |
| Fresh server cycles | New venv's `python -B tests/smoke_server.py` | HTTP 200 twice, both exits 0 | `stage10-fresh-server.log`, `stage10-fresh-server-detail.log` |
| Browser workflows | Isolated temporary save, local browser | All five states, two-cell batch, restart persistence, no-stock guard, reset, full/partial confirmation | `screenshots/`, `verification-log.md` |

The fresh project was copied into
`/var/folders/p_/n1vdxrj147g7_xz3dhbqstcr0000gn/T/transportation4322-fresh-16o7721w`.
It contained source, tests, locked requirements, Streamlit config and sample data;
it did not inherit the normal working save or virtual environment. This is a
same-machine clean setup, not cross-platform evidence. Exact installation commands
and interpreter paths are recorded in the installation log. The personal path is
kept here as execution evidence, not in portable README instructions.

Benchmarks (median of three paired runs, seconds):

| Warehouses × stores × items | Bellman–Ford | Dijkstra | Ratio BF/Dijkstra |
|---|---:|---:|---:|
| 4×4×2 | 0.000180 | 0.000135 | 1.33 |
| 12×12×3 | 0.004491 | 0.002472 | 1.82 |
| 30×30×3 | 0.072958 | 0.030628 | 2.38 |
| 60×60×3 | 0.692739 | 0.204924 | 3.38 |

These measurements are machine-specific, not universal speed guarantees. The
optimizer mutation checks reject three deliberately damaged potential/cost
variants through errors; persistence mutation checks catch assertion failures.

## Critical findings and scope

One active grid cell is edited at a time; many completed edits are saved in one
atomic batch. A bad cell rejects the entire batch. Single-cell helpers remain for
Add/Set/Remove. Text input preserves exact 300-digit integers and integer cents.
The UI must receive a completed cell edit: finish with Enter/Tab and verify the
displayed value before saving. A rapid automation sequence missed the final
uncommitted value; the documented completed-cell sequence passed in the browser.

The first browser workspace experienced unexplained changes on disk relative to
its session, correctly rejecting stale operations. It was not used as clean
acceptance evidence. A new isolated workspace reproduced the complete flows;
see the chronological verification log for the exact observations. The cause of
those initial changes was not established; it is not asserted to be a fixed defect.

Tests are exhaustive only over their stated finite domains. AppTest does not prove
browser appearance or input behavior. Browser checks do not certify every keyboard
path, screen reader, clipboard block paste, browser or operating system. Sequential
stale-state detection is not simultaneous-writer locking. Power-loss directory
persistence and network filesystems remain outside the storage guarantee.

The assignment permits fixed catalogs and ordinary UI libraries. No direct solver
library or linear programming was added. Native Streamlit renders the approved
five states; combined table saving is the requested extension, not a pixel-perfect
copy of the PDF. Original reference files and historical logs remain intact.

## Completion boundary

Technical implementation, automated checks, browser demonstration, portable README,
screenshots, presentation study guide and factual AI-use inventory are prepared.
Student understanding and personal verification are not inferred from agent tests.
The complete chat export, truthful initial-design history, current course deadline
and submission-channel verification, and actual publication/submission still need
attention. The AI-use inventory explicitly identifies the incomplete chat record.
No submission or publication occurred. Cleanup has intentionally not been done.
