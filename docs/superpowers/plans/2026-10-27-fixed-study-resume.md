# Fixed-study acknowledged-failure continuation plan

> **For agentic workers:** Use superpowers:executing-plans inline. No additional agents are needed.

**Goal:** Execute only 536 unstarted cells after the user's explicit “那你继续跑吧？” authorization, preserving 343 completed cells and one runtime failure.

**Architecture:** Add a versioned operations session under `parallel/sessions/`, with an immutable authorization and hashes of all existing attempt files, plan and runtime. The scheduler accepts only the exact acknowledged failure bytes; all new failures and unknown starts still stop claims. Frozen experiment modules, parser, model identities, scores and plan stay unchanged.

**Tech Stack:** Python standard library, existing RunStore, tmux and two private Ollama replicas.

**Spec:** Existing `2026-10-26-fixed-carrier-study-design.md`; this is an operations amendment authorized by the user, not a method change.

## Constraints and review focus

- Acknowledged key is `9e26e7176ccc820d55761adf`; never retry or overwrite it.
- Old management stop/result/queue/logs remain intact. New session creation is exclusive and uses the same global run lock.
- Every new failure stops new claims; in-flight cells drain. Dead or unregistered unfinished owners block continuation.
- Final native audit remains false for the genuine failure. A separate coverage audit may pass only with all 880 terminal cells and that one exact failure; no invented scores.
- Two allowed UUIDs, original endpoints/configuration and ownership-verified cleanup remain unchanged.

## Implementation

- [x] Add failing real-file/process tests for isolated session logs, acknowledged immutable failure, concurrent remaining-only claims, altered evidence rejection, new-error stop, and honest final coverage.
- [x] Add operations session helpers and integrate them into existing scheduler; retain default legacy behavior.
- [x] Run local and Linux scheduling tests, hash deployment, verify frozen source and full existing native partial audit, seal all344 file hashes.
- [x] Launch one new tmux controller; verify two distinct new claims, runtime identity and unchanged original evidence.
- [x] Record actual identities and create quiet 15-minute monitoring. On completion retain original audit limitations, bundle evidence and report, then remove automation.
