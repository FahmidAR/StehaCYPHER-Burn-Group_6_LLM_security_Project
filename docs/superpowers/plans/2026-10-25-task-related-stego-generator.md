# Task-related variable-length acrostic generator

> **For agentic workers:** Use superpowers:executing-plans inline and TDD.

**Goal:** Generate task-related hidden messages at requested letter lengths,
then model-write complete related sentences whose initials reproduce each message.
**Architecture:** New isolated experiments/task_stego package. Model-independent
validators/prompt builders plus an injectable two-stage generator; separate CLI
prepares offline and requires explicit approved-plan SHA for any model request.
**Tech Stack:** Python stdlib offline; existing local Ollama35B via AsyncOpenAI
only after execution approval. No model installation/start, GPU allocation or MAS.
**Spec:** This short plan incorporates the user's explicit request and the scope
rulings below. Earlier user opted out of repeated design questions and requested
code-first/run-approval-later; no new design approval loop.

## Scope / decisions
- One request + exact target letter counts (spaces excluded, default12/17).
- Stage1 generates one shared task-related intent and meaningful English phrases
  at all requested lengths. No fixed VALIDATE, word bank or padding.
- Stage2 generates an array of N full task-related sentences per phrase, initials
  spelling its normalized letters. Keep original sentence text, no letter editing.
- Deterministic checks enforce JSON schema, target lengths, sentence count, terminal
  punctuation, minimal word count and codec-compatible exact initials. Grammar,
  semantic relevance and equivalent meaning remain unverified, not machine gold.
- No automatic retries, repair, fallback templates, model swapping or success-only
  selection. Preserve every raw attempt; API failure stops further requests.
- Generation is a separate artifact, not yet wired into native MAS. Existing
  teammate runner/scorer/616-cell plan remain untouched. Never label generation
  verification as attack efficacy or change native evaluation criteria.
- Optional execution uses original actor model name qwen3.5:35b, one explicit local
  endpoint. Generation API usage/cost are separate from native experiment scores.

## Tasks / review focus
- [x] RED→GREEN tests: exact meaningful phrases, invalid length not repaired,
  punctuation that breaks original sentence codec, raw-text preservation, stage2
  failure in denominator, API failure budget, no approval before optional imports.
- [x] Implement generator.py, cli.py, offline examples/README; lock and immutable
  attempt evidence, no network in preparation.
- [x] Full existing+new suite, fresh whole-change review and one test-backed fix
  pass if needed. No live model/API run until user approves.

## Ledger
Pre-flight: stage1 phrase data feeds stage2; validation must use actual generated
letters, not requested labels. CLI consumes full outcome including failure/unknown.
Ruling: standalone generator only — user now authorizes this missing capability,
not an unannounced replacement of teammate attack generation or evaluation.
Ruling: exact letter lengths, not token targets; natural language cannot be
guaranteed for every exact count, so unsatisfied attempts are honest failures.

## Verification — completed October26,2026

Implementation d670d5d (base d78da97).13 tests initially GREEN after observed RED
for missing generator/CLI and empty-code validation. Fresh whole-change reviewer
found one P2: malformed API envelopes were accessed before retaining raw body.
Added test_malformed_api_envelope_retains_raw_body_and_usage_before_stopping,
observed RED (raw_response missing), then captured/journaled raw response before
validation and carried malformed body/usage through InvalidCompletion.14 new
tests GREEN. No extra reviewer or additional experimental feature added.

Review declined live endpoint compatibility, generation adherence, grammar,
semantic relevance/equivalent intent and efficacy; ruling: all remain explicitly
unverified pending approved real generation and inspection, not scored as true.

Latest per-suite results: generator14, native-ablation18, old-generation38,
analysis18 and ops2 passed (90 total). During the full regression one unchanged
old test, test_shared_budget_is_atomic_across_independent_journals, raised Windows
PermissionError at analysis/effect_scoring.py:122 while concurrently initializing
budget.lock. Exact analysis suite rerun passed18/18. Source diff confirms analysis
unchanged; the initial intermittent failure remains recorded, not erased by the
rerun. It is outside the new generator's imports and was not modified under the
user's restriction on unrelated scoring changes. Existing loader ResourceWarning
also remains inherited.

Offline example plan: results/task-related-stego-prepared-20261026/plan.json,
SHA8d3128167fbca318be46a375f82a5f4bf783ada28ffd3aef6db87e87213ce765.
Verified code hashes,12/17 targets,max3 model requests; no started marker, events,
generated result, OpenAI/AutoGen imports or model requests during preparation.
Native teammate source, scorer and616-cell config hashes remain unchanged.
No GPU/server/deployment/push/automation. Keep worktree for user run approval.
