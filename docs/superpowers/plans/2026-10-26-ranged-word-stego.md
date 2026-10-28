# Ranged word stego implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; one fresh review of
> the whole change at the end. User has authorized implementation and small testing.

**Goal:** Generate task-related hidden messages in three length bands and complete
word-initial paragraphs, with strict validation and bounded transparent correction.

**Architecture:** New pure ranged.py module reuses Completion/strict_json/carrier_words;
existing CLI selects by a new schema. Old exact mode stays unchanged. No native MAS edits.

**Tech Stack:** Python stdlib/unittest, existing OpenAI SDK, local Ollama35B.

**Spec:** docs/superpowers/specs/2026-10-26-ranged-word-stego-design.md

## Global Constraints

- Default bands4–8,9–14,15–24; max2corrections/stage;12calls/task inclusive of failure.
- Original35B,reasoning_effort=none,8192tokens/request,retries0,timeout300s.
- Every word contributes, whole words only, multiple sentences, raw evidence preserved.
- Structural checks are not semantic gold; no MAS/judge/baseline/defense invocation.
- GPU0 only if idle; disable Vulkan; detach/cleanup/verify; preserve all historical outputs.

## Review Focus

- Correction never edits accepted phrases or discards failed attempts.
- Invalid caller band/budget/schema rejected before model import or started marker.
- Wrong/missing/extra word feedback accounts for every function word and punctuation.
- API failures preserve raw envelopes/cost and earlier completed variants.
- Frozen plan hashes both new and reused source and cannot be silently mixed/restarted.

## Task1: Ranged generation and CLI

Files: create experiments/task_stego/ranged.py and tests/test_ranged.py;
modify cli.py,tests/test_cli.py,README.md.
Interfaces: generate_ranges(request,bands,complete,max_repairs=2,sink=None) -> result;
validate_bands(bands),validate_paragraph(value,code); prepare_ranged(...) -> signed plan.

- [x] Write tests for band validation, paragraph words, count/initial feedback, limited
  repair, exhausted attempts, API raw failure and CLI freeze/dispatch/no restart.
- [x] Run RED; implement minimal code; run focused GREEN.
- [x] Run all5test directories; inspect diff/native preservation; commit exact files.

## Task2: Review and bounded real smoke

- [x] One fresh reviewer checks task1 as a whole; fix important findings RED/GREEN once.
- [x] Check GPU/process ownership, upload frozen code/controller, launch one tmux smoke.
- [x] At most12fresh calls; no new automatic whole-plan retry or model switch.
- [x] Audit attempts/rawusage/decoding and download full evidence; verify GPU release.
- [x] Report actual English/Chinese outputs, failed corrections, semantics pending and
  limits; update ledger and commit report. Do not label hand-written text as model output.

## Progress ledger

Base:d8de975; existing linked worktree feat/teammate-final reused, clean before changes.
Pre-flight: CLI consumes the ranged module; exact callback signature stays unchanged.
Ruling: named word array is joined only, not silently repaired; it makes every index visible.
Ruling: range mode is explicit, not a replacement of old exact plans or616native protocol.

Task1 complete: new10generator tests and2CLI tests RED/GREEN; existing exact tests retained.
Whole-change review by /root/review_ranged_word_generator found2important evidence/protocol
issues,0critical,0minor. Both fixed in one pass: contradictory frozen model/token/retry/
timeout fields now fail before started marker; HTTP exception body/status/text/request_id
retained. Two reproductions RED/GREEN; full suite114/114(38+18+18+2+38), inherited loader
ResourceWarning only. No runtime generation change made after freezing a real plan.
Review rulings: actual grammar/relevance/intent equality/live efficacy are intentionally
unverified and pending; lifecycle will be checked by the smoke, not inferred from unit
tests; MAS integration/placement is outside this step and remains unlaunched.

Task2 complete: frozen380a533 smoke used12fresh calls, all nonempty/stop,7187prompt+
474completion=7661tokens. Short8words decodes, wording awkward; medium13initials match
but final s. is invalid filler; long22target/21words failed. Human/semantics pending.
Live-detected ruling: single-letter s. shows lexical guard gap; RED/GREEN test added,
future ranged validation now rejects standalone letters except a/I. NO regeneration,
no historical result overwrite, archive frozen before guard patch. Full suite115/115.
Own CUDA GPU0 service391407 used17second service window, exited; port free,8cards2MiB/0%.
All evidence downloaded and code hashes/usage/12attempts verified; report at
docs/results/2026-10-26-ranged-word-stego-smoke.md. No full MAS or placement run started.
Keep existing worktree/branch per ongoing user workflow; no merge/push/PR or cleanup.
