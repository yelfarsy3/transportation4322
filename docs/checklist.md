# Course and project checklist

Updated 2026-11-09. Deadlines below are not evidence of submission status.

## Source inventory and authority

- Course ZIP in parent `sources/`: syllabus4322.pdf (1 page), policy4322.pdf
  (2 pages), Technical interviews.pdf (1 page), table of contents. No nested ZIPs,
  project starter code, assignment, or announcements were present.
- Desktop `transportation4322/1 Transportation.pdf`: assignment, p. 1;
  copied as `reference/assignment-transportation.pdf`. Same SHA-256 as recovered chat copy.
- Desktop `transportation4322/0 general instructions.pdf`: general project rules,
  pp. 1-2; copied as `reference/general-instructions.pdf`.
- Desktop UI PDF and recovered chat UI PDF are byte-identical; preserved as
  `reference/initial-ui-design.pdf`, p. 1, panels 01-05. Visually inspected.
- `reference/earlier-planning-transcript.txt` is a prior AI discussion, not an
  instructor instruction document. Later approved plan overrides its old
  all-or-nothing recommendation.
- `approved-plan.md` is the approved ten-stage plan from “Restock Algorithm Planning.”
- Brightspace live announcements were not checked in this session. Current
  announcements, assigned presentation date and submission deadline remain unverified.

## Gates

- [x] Stage 1 technical setup: venv, Streamlit, app test, two server cycles, Git checkpoint.
- [x] Stage 2 agent verification: exact sample, validated state, focused tests.
- [x] Stage 2 personal verification: user reported on 2026-11-08 that the checks made sense and answers matched; user marked the exercise Done.
- [x] Stage 3 availability, demand and shortage functions: agent-tested.
- [x] Stage 3 personal check marked done by the user; subsequent audit requested and gaps fixed.
- [x] Stage 4 independently checked tiny brute-force reference: agent verification complete.
- [x] Stage 4 check marked done by the user; original edit preserved.
- [x] Stage 5 Bellman–Ford minimum-cost maximum-flow: agent-verified.
- [x] Stage 6 Dijkstra with potentials, comparisons, complexity and benchmarks: agent-verified.
- [x] User reported reviewing/verifying Stages 5–6 in chat on 2026-11-08.
- [x] Stage 7 preview, cancellation, stale-plan checks, once-only confirmation: agent-verified.
- [x] Stage 8 atomic JSON persistence and restart/reset checks: agent-verified.
- [ ] Student personal explanation/verification for Stages 7–8.
- [x] Stage 9 approved five UI states, atomic batch editing and agent browser walkthrough.
- [x] Stage 10 technical validation: 113 tests in three environments/settings, audits, browser demo, screenshots and presentation guide.
- [ ] Stage 10 student completion: personal checks/explanation, full chat export, design history, current course instructions and actual submission.
- [ ] Cleanup: intentionally deferred at the user’s request.

## Course dates, deliverables and next actions

| Item | Source | Status / next action |
|---|---|---|
| Nov 12, 17, 19 project presentations | Syllabus p. 1, tentative | Verify assigned date and newer announcements; no deadline inferred |
| Project itself, GitHub recommended or email | General instructions p. 1 | Local work only; not published or submitted |
| Initial design | General instructions p. 1 | Preserve original and accurately describe design history |
| AI chat log and detailed stage checks | General instructions p. 1 | Preserve current chat and linked prior chats; student adds personal evidence |
| AI, language and technology list | General instructions p. 1 | Codex, Python, Streamlit; dependencies recorded |
| Understand algorithm and runtime | General instructions p. 2; assignment p. 1 | Discuss as implemented; separate written submission not required |
| No linear programming or direct algorithm library | Assignment p. 1; general instructions p. 2 | Two handwritten flow solvers plus testing reference; no optimization library |
| Own AI prompts; own verification | General instructions p. 1 | No prompts generated; Stages 2–6 confirmed; Stages 7–8 personal explanation pending |
| Attendance | Policy p. 1 | No attendance claims made |

## Practice log

2026-11-08: state invariants, stable IDs, integer cents, copying versus mutation.
Student mistakes and explanation quality: not assessed yet. Next revisit: before
Stage 3, using `understanding-check.md`. No claim of mastered understanding.

2026-11-08 follow-up: user reports Stage 2 understanding and matching verification answers.
Stage 3 focus: per-item totals, why aggregate stock cannot replace item-by-item
checks, and why prices do not affect maximum shipment counts. Revisit before Stage 4.

2026-11-08 Stage 4: exhaustive search, restoring state between recursive branches,
ordered objectives, independent reference methods, and search limits. Student
explanation quality not assessed; revisit before Stage 5.

2026-11-08 Stages 5–6: residual reassignment, shortest augmenting paths, potentials,
reduced costs and time complexity. Personal explanation quality unassessed; revisit
using the two new understanding documents before Stage 7.

2026-11-08 Stages 7–8: snapshot identity, stale confirmation, copy-before-commit,
atomic replacement, lost acknowledgments, reload and outstanding demand. Revisit
with the two new understanding checks before Stage 9.
