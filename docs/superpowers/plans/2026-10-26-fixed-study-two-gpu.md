# Fixed study two-GPU scheduling amendment

> **For agentic workers:** Use superpowers:executing-plans inline. User explicitly authorized adding a second GPU; no new scientific method is authorized.

**Goal:** Finish the existing 880-key plan faster with two independent identical model replicas, preserving all started keys.

**Architecture:** Keep all frozen experiments modules byte-identical. An operations-only controller owns the original run.lock, starts one original Ollama replica per GPU (0/1, ports11435/11436), and uses two isolated Python processes sharing atomic key claims. Only the controller exports and audits after both workers drain. Original plan remains unchanged; physical endpoints and per-key allocations are separately recorded.

**Tech Stack:** Existing Python/AutoGen/Ollama, POSIX permissions/flock, tmux; no dependencies or model pulls.

**Design decision:** Live duplication would race the original controller's final export/audit. Drain the original run at a key boundary by temporarily removing write permission on the attempts parent directory: the existing in-flight directory remains writable and can finish, while creating the next key directory fails before started.json. Preserve the expected management-only exit and all logs; restore exact original permissions after the old process and its owned service exit. Test this against the real legacy execute_pending loop on Linux before deployment. No signals to an in-flight request, fabricated starts, or key retries.

## Constraints / review focus

- Exactly the original880 keys, native generation/scoring, original88 task/code/data/plan hashes.
- Resume only if every started key is completed and actual-I/O audit passes; never retry a started failure.
- Claim+finish use a short cross-process lock; prior failure halts new claims but lets already active work finish.
- GPU1 must be idle immediately before launch; per-server UUID isolation, Vulkan=false, parallel1/maxloaded2 and original defaults.
- Worker transport endpoint may differ, but metadata/model/package identity must equal original runtime after endpoint normalization. Frozen plan is never rewritten.
- Owned-process cleanup only; original results' SHA snapshot must remain unchanged.

## Tasks

- [x] Local RED/GREEN: concurrent unique claims (barrier ensures both workers active); preserved started keys; failure stops new claims; dead/PID-reused owner and foreign journal rejected; endpoint identity rejection.
- [x] Implement ops/fixed_study_parallel.py outside frozen tree; local full six-suite run:139 tests,136 passed,3 POSIX-only skipped. Frozen extension hashes unchanged; git diff --check clean.
- [x] Linux-only permission-boundary, signal drain and orphan model-session cleanup tests: server observed9/9 RED before module upload, then9/9 GREEN with implementation. bash -n passed; all three operational file SHA values match local.
- [x] Deployed and tested Linux drain fixture; real boundary drain finished110 original keys, no failed/unknown started key. Sealed332 original files with immutable SHA manifest and downloaded closed110 evidence archive; local UTF-8 offline audit passed.
- [x] Detached two-GPU controller982662, workers984265/984266, servers983583/983635. Both GPUs performed real independent actor work with distinct keys and unchanged runtime identities.00:35:10Z111 completed, issues=[]; GPU1 real14 actor outputs and judging underway; GPU0 finished one new key and started another.
- [x] Progress and automation updated to actual two-GPU state and own-service identities. Do not infer speed from first few minutes; keep full880 experiment follow-up active.

## Ledger / review

2026-10-27T00:27Z (Chicago Oct26 evening): all SSH probes fail during banner exchange; no operations code or tests deployed remotely and no claim fence set. Existing detached serial job is untouched. Continue deployment via existing heartbeat after connectivity returns; no changes to VPN or SSH.

Read-only independent review found four material management issues. One fix pass added signal-driven draining with isolated worker sessions, PID+OS-birth identity and liveness checks, foreign-journal inventory validation, and verified owned-session descendant cleanup even after the server leader exits. Cleanup errors now force nonzero controller result. Local claim/ownership regressions were observed RED then GREEN. Signal/drain/descendant tests are present but Windows cannot execute them; do not claim Linux verification until all9 focused tests pass on erb204. No second review requested.

Ruling: infrastructure amendment lives under ops/, outside original extension hash, with its own controller operations SHA and per-key allocation ledger. User explicitly authorized two cards; plan/source/model/data/scoring remain byte-identical. Risk if wrong is duplicated or mixed runs, covered by atomic transaction lock, all-key inventory, start journals, runtime checks, frozen native audit and pre-transition SHA validation.

Ruling: temporary parent-directory write fence is a management-only boundary stop. It intentionally produces a logged PermissionError before the next key is started; it must never be represented as a failed model attempt or be used to erase a real failure. Existing in-flight files stay writable; source and scoring trees are untouched. Real Linux test is mandatory before setting it.

2026-10-27T00:31:36Z: user reported connectivity restored. Checked109 completed with no finished-I/O issues, GPU1 idle. Deployed only three new ops/test files; Linux9/9 and syntax/hash checks passed. Started one detached tmux scb-fixed-study-two-gpu-20261026, transition wrapperPID982662. It set the tested claim fence at00:31:38Z and waits for original worker619926 to finish key9d9abb2d3b27320b39fbcbff. No request interrupted or key retried. Two-GPU services are not yet started at this timestamp; wrapper will seal/audit and launch after legacy cleanup.

2026-10-27T00:32:15Z: transition sealed110 completed keys. Original controller expected management exit1 is retained; old model process stopped. New controller982662 starts GPU0/1 replicas at11435/11436.00:33:02Z both GPUs27452MiB/79%, separate real actor output; model/package metadata equal after endpoint normalization.00:35:10Z111 completed, all completed actual-I/O checks clean. Original plan/source/data/runtime and all sealed evidence remain byte-identical. Same full880 matrix, no pilot/new calibration/retry.

Archive: results/fixed-study-two-gpu-transition-20261026/pre-two-gpu-110-evidence.tar.gz,
4610075 bytes, SHA256500c5a860a8712ff20ce2c4bb0659c45377d21070b05addfe8889e5205504561.
110 sealed raw attempts and source/identity/tests/transition records retained. Local audit(allow_unstarted=True) ok=true,110 started/880 required,issues=[]; first local read used Windows cp936 and failed task hash validation, corrected to explicit UTF-8 with no file/data modification, then verified original exact88-task SHA. This is evidence/dispatch completion only, not a full experiment or effect conclusion.
