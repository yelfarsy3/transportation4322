# UI redesign, scenarios and teaching features — 2026-11-13

Agent-prepared record (Claude Code, `claude-opus-5-5`). It describes what was
built and which checks were actually run. It is not student verification.

## Design plan

Subject: a restock dispatch tool for a classroom demonstration of minimum-cost
flow. Audience: instructor and classmates on a 1366×768 projector. Primary job:
show the data, the plan and why the plan is optimal in one window.

| Token | Hex | Role |
|---|---|---|
| harbor | `#0F2233` | Sidebar and network board ground |
| chart | `#EDF1F4` | Page ground (cool chart-table grey) |
| slate | `#DCE4EA` | Inputs, table headers |
| signal | `#0A6E80` | Actions and links on light ground |
| glow | `#52DCEB` | Units moving on the board (navy ground only) |
| undo | `#FF6B6B` / `#B3372F` | Reassignment on navy / errors on light |

Colors live in `.streamlit/config.toml`; `theme.py` reads that file for the
board, which adds only its own navy-context tones. Measured WCAG contrast:
ink on chart 13.3:1, muted text 5.4:1 (4.8:1 on slate), white on signal 5.9:1,
glow on harbor 9.9:1, red on harbor 5.8:1. All pass AA.

Type: **Barlow** (body, tables, buttons) and **Barlow Semi Condensed** (headings,
board figures), one superfamily. Barlow is drawn from California highway signage,
which suits freight routing, and the semi-condensed width fits more numbers per
line. Self-hosted from `static/fonts/` (SIL Open Font License 1.1, `OFL.txt`),
served by Streamlit static serving and loaded by the board from the same files.

Principles: spend the boldness on the network board only; color carries meaning
(cyan = units moving, red = reassignment), never decoration; every screen's key
data fits one laptop window.

### Self-review against generic defaults (what changed)

1. **KPI tiles replaced.** A row of big-number tiles was the first idea; it is a
   stock dashboard treatment. Replaced by one plain sentence headline
   ("8 units ship for $16.00. All store demand is met.").
2. **Dark + single neon accent avoided as a page theme.** Only the board and
   sidebar are navy; the working surface is light for projector legibility.
3. **No card kit.** Content sits directly on the page ground; only the board is a
   panel. Small 6px radius for inputs, pill buttons to echo the board controls.
4. **Template chrome removed.** No all-caps eyebrows, no monospace data labels,
   and the old middle-dot meta strings ("10 units · Shipping cost") were rewritten.
5. **Red reserved.** The partial-restock headline was first red; red already
   means reassignment on the board, so the headline went back to ink.

## Layout options considered

```
A  Sidebar + wide two-column main (chosen)
┌──────────┬───────────────────────────────────────────┐
│ Title    │ Restock preview              [Confirm]    │
│ Scenario │ 8 units ship for $16.00…     [Cancel ]    │
│ [Load]   ├────────────────────┬──────────────────────┤
│ Saved    │ Proposed shipments │ [Explore algorithm]  │
│ Reload   │ Why optimal        │  network board       │
│ Reset    │ vs cheapest-first  │                      │
│          ├────────────────────┴──────────────────────┤
│          │ tabs: availability │ stock after │ demand  │
└──────────┴───────────────────────────────────────────┘

B  Top tabs (Data | Plan | Algorithm): rejected, hides data behind tabs.
C  Three columns (tables | plan | board): rejected, each too narrow at 1366px.
```

Stock screen under A: the three editable tables side by side (width proportional
to each table's column count), a supply-and-demand-by-item table, and the
actions beside it. Confirmation: updated stock and remaining demand side by side.

## Scenarios

Files: `data/scenarios/*.json` (read-only; the working file may not point there).

| Scenario | Size (W×S, items) | Units | Optimal | Cheapest-first | Paths | Reassignment steps | Verified by |
|---|---|---|---|---|---|---|---|
| Course sample | 2×2, 2 | 10 | $14.00 | $14.00 | 4 | 0 | brute force + certificate |
| Greedy trap | 2×2, 1 | 8 | $16.00 | $44.00 | 2 | 1 | brute force + certificate |
| Chained reassignment | 3×3, 1 | 4 | $10.00 | $15.00 | 3 | 2 (in one path) | brute force + certificate |
| Shortage | 3×3, 1 | 10 | $23.00 | $23.00 | 3 | 0 | brute force + certificate |
| Surplus | 3×3, 1 | 12 | $30.50 | $30.50 | 3 | 0 | brute force + certificate |
| Equal-cost ties | 2×3, 2 | 15 | $45.00 | $45.00 | 8 | 0 | brute force + certificate |
| Free routes, empty locations | 3×3, 1 | 10 | $2.00 | $2.00 | 3 | 0 | brute force + certificate |
| Skipped items | 2×2, 3 | 8 | $18.00 | $18.00 | 3 | 0 | brute force + certificate |
| Items plan independently | 3×3, 3 | 27 | $78.00 | $78.00 | 10 | 0 | brute force + certificate |
| Regional stress test | 4×5, 3 | 137 | $421.25 | $427.25 | 19 | 3 | certificate only |
| Reassignment cascade | 3×3, 1 | 7 | $30.00 | $39.00 | 6 | 5 | exhaustive + exact trace |

**Reassignment cascade** is the single traceable proof case (`tests/test_cascade.py`).
It was chosen by searching random 3×3 networks for the most reassignment steps
and largest greedy gap, keeping only cases with one optimal plan and a unique
cheapest path at every step. The $1 route (Central→A) is used first, then fully
undone; the optimum does not use it.

| Path | Route (⟵ = reassignment) | Units | $/unit |
|---|---|---|---|
| 1 | Central→A | 2 | 1 |
| 2 | South→A | 1 | 2 |
| 3 | South→A ⟵Central, Central→B | 1 | 2−1+4 = 5 |
| 4 | North→A ⟵Central, Central→B | 1 | 3−1+4 = 6 |
| 5 | North→A ⟵South, South→B | 1 | 3−2+6 = 7 |
| 6 | North→A ⟵South, South→B ⟵Central, Central→C | 1 | 3−2+6−4+5 = 8 |

The test pins every path and the allocation after each one, checks Bellman–Ford
takes the same paths, enumerates all 19 complete plans ($30 to $42; only one at
$30, and every plan using the $1 route costs more), and shows cheapest-first pays
$39 while the certificate finds the cheaper loop it missed.

Every scenario is also checked for Dijkstra = Bellman–Ford totals and for its
stored expected totals (`tests/test_scenarios.py`). Reassignment claims are
asserted from the recorded trace, not assumed.

**Certificate** (`teaching.certify`): rebuilds the residual network from the final
shipments alone and runs Bellman–Ford for a negative-cost cycle. A maximum-quantity
allocation with no such cycle has minimum cost. The certificate itself was tested
against brute force on 120 random tiny networks, over every maximum allocation:
it accepted exactly the minimum-cost ones.

**Load scenario** asks for confirmation, replaces the working file through the
existing stale-save check (revision advances once), clears any preview, and never
writes the scenario files. Regular commits still refuse catalog changes. After a
scenario load, Reset to sample uses the same guarded replacement.

## Features

Implemented:

| Feature | Benefit |
|---|---|
| Network board on the preview | The plan is visible as routes, not only a table |
| Explore algorithm replay | Shows each selected augmenting path, reassignments in red |
| Previous / Next path stepping | Presenter controls the pace |
| Why this plan is optimal | Plain-language independent certificate |
| Cheapest-first comparison | Shows the cost of greed and the missed rearrangement |
| Scenario loader | Ten prepared cases covering the algorithm's decisions |

Recommended, not implemented: a read-only board on the stock screen (more height
on the busiest screen); highlighting edited cells before saving (Streamlit's grid
does not expose per-cell styling for edits); per-item cost column in the
shipments table (the board's Details already lists it).

## Verification actually run

- Full suite: 139 tests passed (132 before the cascade case) (`docs/evidence/ui-redesign-tests.log`), up from 113.
- Browser (Chrome, local server, temporary state file): every screen state,
  scenario load confirmation, partial and full flows, replay with a reassignment,
  Details, Pause/Resume, Previous/Next including boundaries. Screenshots in
  `docs/screenshots/`.
- Font: `document.fonts` reported Barlow and Barlow Semi Condensed loaded from
  `/app/static/fonts/`.
- Reduced motion: checked on a standalone copy of the board with
  `prefers-reduced-motion` forced on; the glow became a static highlight and the
  captions kept their reading time.

## Not verified or unresolved

- The browser viewport available was 1512×771 (and 1366×700); 1366×768 and
  1920×1080 could not be produced exactly on this display.
- No screen-reader, cross-browser or mobile testing.
- In a 4×5 network the stock tables scroll sideways beside the sidebar, and some
  unit labels on crossing lanes overlap.
- Editing source files while a session is open makes Streamlit reload modules,
  after which that open session can raise a type error; restarting the server cleared
  it here. This is development-time behavior that also applied before this change.
