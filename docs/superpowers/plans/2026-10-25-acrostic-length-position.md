# Acrostic length/position implementation plan

SUPERSEDED by 2026-10-25-teammate-ablation-correction.md under the user's narrower
instruction: native generation/runtime/scoring; only length and receiver position.

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Add an offline-preparable, approval-gated teammate-compatible factorial experiment.
**Architecture:** New experiments/acrostic_ablation modules consume a pinned upstream source snapshot; old source and results remain untouched. Pure planning/storage/reporting is separate from live AutoGen imports.
**Tech Stack:** Python stdlib for offline steps; teammate AutoGen/OpenAI/Ollama for later approved execution.
**Spec:** docs/superpowers/specs/2026-10-25-acrostic-length-position-design.md

## Global Constraints
- No model requests, server launch or GPU use before user approval.
- Pin teammate 9a60c83; 35B actor/8B judge, 88 tasks, B3, trial1, MAX_TURNS12.
- Two literal payloads (12/17 letters), before/after/system-memory; 616 default runs.
- Preserve old generation/analysis/result files. Labels remain legacy proxies, human pending.

## Review Focus
- Malformed/empty/non-ASCII payloads must fail; sentence punctuation cannot corrupt initials.
- Same carrier bytes and query across placements; memory authority/exposure disclosed.
- Same task/trial shared clean; no accidental duplicated or pooled unpaired baselines.
- Wrong approval/hash/code/source must fail BEFORE importing/calling model libraries.
- Crashed/started cells never silently retried; model service error trips circuit breaker.

### Task 1: Payloads and matrix
**Files:** experiments/acrostic_ablation/design.py; tests/test_design.py
**Interfaces:** normalize_payload, make_carrier, prepare_inputs, build_plan.
- [x] Write failing tests for 12/17 initials, punctuation, placements and 616 unique runs.
- [x] Verify RED, implement pure functions, verify GREEN, commit.

### Task 2: Pinned source, journal and CLI gate
**Files:** baseline.py, storage.py, cli.py; tests/test_storage.py
**Interfaces:** source_snapshot, load_tasks, freeze_plan, claim, terminal, require_approval.
- [x] RED tests for tampered manifests, duplicate starts, all-terminal failure retention and no-approval no-network behavior.
- [x] Implement immutable source extraction, task loading and OS lock, then GREEN.

### Task 3: Native runtime and reporting
**Files:** runner.py, report.py; tests/test_runtime.py, tests/test_report.py; README.md.
**Interfaces:** run_cell(task,cell,plan,upstream), summarize(plan,results).
- [x] RED tests at external boundary: assembled inputs, actual usage fields, original query, error/close and no retry.
- [x] Implement native framework adapter, complete JSONL/raw records and paired length/placement summaries; GREEN.
- [x] Prepare real 88-task offline plan if original data available; no approved model/API run.
- [x] Fresh whole-change review, one RED/GREEN fix pass, full old+new tests and explain exact implemented scope.
