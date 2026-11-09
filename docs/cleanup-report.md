# Cleanup and private GitHub preparation — 2026-11-09

- Committed the student's existing Stage 2–4 verification annotations unchanged.
- Moved 33 historical logs into `docs/evidence/`, preserving every byte. The
  evidence index records SHA-256 checksums. Updated prose references and added
  a documentation index; original reference files were not modified.
- Removed only generated Python caches and the root Finder metadata file.
  Retained the working virtual environment and current inventory locally.
- Added ignore rules for other working JSON files, environment credentials,
  Streamlit secrets, coverage caches and fresh `local-*.log` outputs.
- Changed the server smoke check to write an ignored local log, preventing it
  from overwriting historical evidence. No application/algorithm behavior changed.
- Full regression suite: 113 passed in 5.210 seconds. Both server cycles returned
  HTTP 200 and exited 0. Local logs: `evidence/local-cleanup-tests.log` and
  `evidence/local-cleanup-server.log` (intentionally not published).
- Checked local Markdown links, compared all 33 log files against their prior
  Git versions, and compared original references and sample data byte-for-byte.
- No recognizable private-key, GitHub-token or AWS access-key patterns matched
  the scanned working project files (excluding environment/Git/cache directories).
  This is a focused check, not a comprehensive secret-security certification.

User selected a private `yelfarsy3/transportation4322` repository. Stage history
is retained, including historical local paths and the existing Git author identity.
Those facts are documented, not falsely described as scrubbed from history.
No force-push or history rewrite is needed. Instructor submission, complete chat
export and student verification remain separate from this repository backup.
