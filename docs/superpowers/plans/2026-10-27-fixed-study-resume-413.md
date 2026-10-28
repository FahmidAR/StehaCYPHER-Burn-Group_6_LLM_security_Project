# Remaining 413 cells: second explicit continuation amendment

> **For agentic workers:** Use superpowers:executing-plans inline and request a read-only operations review.

**Goal:** User's latest “继续” authorizes only the 413 unstarted cells, retaining 465 completed and two immutable runtime errors. No parser/model/timeout/scorer changes and no failed-key reruns.

**Architecture:** Extend the existing operations session code with a second exact profile, `resume-20261027-b`. It validates the immediately preceding named session cleanup and hashes, seals all467 existing attempts/plan/runtime, and authorizes only the two investigated failure keys. All new errors still stop claims. Native audit semantics stay unchanged; complete coverage now requires878 completed plus two retained runtime errors.

**Files:** `ops/fixed_study_resume.py`, its existing tests, a separate launch script, and progress documentation. Frozen `experiments/` is unchanged.

- [x] Add failing tests for two preserved failures, concurrent remaining-only claims, third-failure stop and exact start/pending/error scope.
- [x] Add exact second profile and prior-session validation; retain old profile for history without weakening future-failure gates.
- [x] Run local/Linux scheduling tests, read-only review, SHA match against local467 closed archive, and frozen source/data/native partial audit.
- [x] Start only one new tmux session on GPU0/1; verify new distinct claims, process ownership, runtime identity and all old file SHA.
- [x] Record verified identities and recreate quiet15-minute monitoring; report completed coverage honestly with both real failures retained.
