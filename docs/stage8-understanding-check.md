# Stage 8: local JSON persistence and failure recovery

`storage.py` provides JsonStore. `RestockSession.open(store)` loads existing state;
`store.initialize(sample)` explicitly creates a first save and refuses to overwrite
anything already there. Missing, corrupt, invalid-schema or unreadable files raise
StorageError. They never silently reset to sample.

Default location: `data/current_state.json`, separate from immutable `data/sample.json`.
The default path is relative to the module, not the terminal's working directory.
The save contains the full validated State: catalogs, stock, demand, integer-cent
prices, schema version and revision. Previews are not persisted and reopening
requires a new preview. The application screen is still the Stage 1 placeholder;
Stage 9 will connect this backend to the approved interface.

## A commit, in order

1. Build and validate the entire candidate state without changing the old one.
2. Check that the saved state still equals the expected full snapshot. Revision
   alone is not sufficient. A sequential stale session gets StorageConflict.
3. Write JSON to a separate temporary file in the destination directory, flush
   it, and fsync that file. Writing in the same directory keeps replacement on
   the same filesystem.
4. Replace the current file atomically with os.replace. Initial creation instead
   uses a no-clobber hard link so an existing save cannot be overwritten.
5. Only after the store returns successfully, publish the new State in the
   session and discard the preview handle.

Preview, cancellation and no-op edits do not write files. Changed quantities,
changed costs, confirmation and explicit reset each persist one complete state.
Reset restores sample values while increasing the current revision, preventing
old previews from becoming valid again. Sample/reference paths and symlink targets
are refused as writable stores. The original sample is never the working save.

## Failure distinctions that matter

- Before replacement: staging/flush/fsync/replace failures preserve the old save
  and old in-memory state; the active preview can be retried after the cause is fixed.
- After replacement but before the caller receives success: disk may already hold
  the new state. Reload before deciding what happened. A repeated old confirmation
  fails the saved-snapshot check, preventing a second deduction.
- Process exit before replacement may leave an orphan temporary file. Loading
  ignores it and uses only the designated state file. It does not guess that an
  orphan is newer or recover automatically from a corrupt current file.
- A cleanup error must not report a successful publication as a failed commit.
  Cleanup is best effort; abandoned temp files are not active application state.

This is one local user, not a multi-process database. Snapshot comparison and
replacement are not protected by a cross-process lock; simultaneous writers are
outside scope. File fsync plus atomic replacement protects the tested local process
interruption cases. The containing directory is not fsynced, so survival of a sudden
power loss, filesystem failure or network-filesystem behavior is not guaranteed.
There is no backup/history or automatic corruption repair in this stage.

## Critical checks actually performed

- Corrupt/empty/non-UTF8 JSON, invalid quantities, duplicate keys, missing saves,
  invalid destination paths, symlinks, changed catalogs and revisions are rejected.
- Partial-restock demand survives a new session and an actual fresh Python process.
- Sequential stale sessions and manual same-revision price edits are rejected.
- Injected creation, partial-write, flush, fsync and replacement failures preserve
  the prior bytes and session. Edits and resets obey the same failure semantics.
- Actual child processes terminate immediately before and after replacement:
  reopening yields the complete old or complete new State, respectively.
- A simulated lost acknowledgment after publication cannot double-deduct on retry.
- All 512 length-three action traces over preview/confirm/cancel/add stock/add
  demand/change price/reset/reopen match a separate scalar model and saved file
  at every step. Stage 7 also covers all 2,401 four-action in-memory traces.
- Removing active-handle checking, removing snapshot checking, or skipping the
  persistent commit is detected by the tests. Mutants exist only in memory.

These are explicit finite domains and selected failure points, not an assertion
that every possible machine failure or interaction has been exhaustively tested.

## Your repeatable demonstration

Run from the project folder:

```sh
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B tests/audit_transactions.py
.venv/bin/python -B - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from data_model import State
from operations import RestockSession
from storage import JsonStore
sample = State.from_json(Path('data/sample.json').read_text())
with TemporaryDirectory() as folder:
    store = JsonStore(Path(folder) / 'state.json')
    store.initialize(sample.with_quantity('demand', 'store_y', 'monitors', 6))
    session = RestockSession.open(store)
    preview = session.preview()
    print('Preview:', preview.plan.units_shipped, preview.plan.total_cost_cents)
    session.confirm(preview)
    reopened = RestockSession.open(store)
    print('Saved outstanding monitors:', reopened.state.demand['store_y']['monitors'])
    reopened.edit_quantity('inventory', 'warehouse_b', 'monitors', 2, 'add')
    next_preview = reopened.preview()
    print('Next restock:', next_preview.plan.units_shipped, next_preview.plan.total_cost_cents)
    reopened.confirm(next_preview)
    print('Remaining monitors:', store.load().demand['store_y']['monitors'])
PY
```

Expected: preview 12 units/2000 cents; after reopen 2 monitors outstanding; next
restock 2 units/200 cents; then zero monitors outstanding. This example uses a
temporary save and leaves your working save and sample untouched.

Explain why corrupt input must not silently reset to sample, why a lost success
message is different from a rejected write, and why retrying an old preview cannot
deduct twice. Personal Stages 7–8 explanation/verification remains pending.

Storage work is O(state size) serialization and validation per commit, with a full
temporary copy on disk. Plan validation/application is O(n1(n2+n3)+n2*n3+P), where
P is the positive-shipment count; it uses copied state tables and a set of P route
keys. Preview additionally pays the optimizer's cost. None of these helpers
implements the UI, multi-user locking, backup history or real-world deliveries.
