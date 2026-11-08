# Course and project checklist

Recorded 2026-11-08. Deadlines below are not evidence of submission status.

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
- [ ] Stage 3 student understanding/personal verification.
- [ ] Stage 4 independently checked tiny brute-force reference.
- [ ] Stage 5 minimum-cost maximum-flow with negative residual edge support.
- [ ] Stage 6 faster shortest-path method and complexity explanation.
- [ ] Stage 7 preview, cancellation, stale-plan checks, once-only confirmation.
- [ ] Stage 8 atomic JSON persistence and restart/reset checks.
- [ ] Stage 9 approved five UI states and browser walkthrough.
- [ ] Stage 10 complete demonstration and submission materials.

## Course dates, deliverables and next actions

| Item | Source | Status / next action |
|---|---|---|
| Nov 12, 17, 19 project presentations | Syllabus p. 1, tentative | Verify assigned date and newer announcements; no deadline inferred |
| Project itself, GitHub recommended or email | General instructions p. 1 | Local work only; not published or submitted |
| Initial design | General instructions p. 1 | Preserve original and accurately describe design history |
| AI chat log and detailed stage checks | General instructions p. 1 | Preserve current chat and linked prior chats; student adds personal evidence |
| AI, language and technology list | General instructions p. 1 | Codex, Python, Streamlit; dependencies recorded |
| Understand algorithm and runtime | General instructions p. 2; assignment p. 1 | Discuss as implemented; separate written submission not required |
| No linear programming or direct algorithm library | Assignment p. 1; general instructions p. 2 | No optimizer implemented or library added |
| Own AI prompts; own verification | General instructions p. 1 | No prompts generated; Stage 2 verified per user, Stage 3 personal check pending |
| Attendance | Policy p. 1 | No attendance claims made |

## Practice log

2026-11-08: state invariants, stable IDs, integer cents, copying versus mutation.
Student mistakes and explanation quality: not assessed yet. Next revisit: before
Stage 3, using `understanding-check.md`. No claim of mastered understanding.

2026-11-08 follow-up: user reports Stage 2 understanding and matching verification answers.
Stage 3 focus: per-item totals, why aggregate stock cannot replace item-by-item
checks, and why prices do not affect maximum shipment counts. Revisit before Stage 4.
