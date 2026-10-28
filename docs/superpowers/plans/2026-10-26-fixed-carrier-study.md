# Fixed carrier880runstudy implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline and one fresh final
> review; user authorized small testing and formal same88-task volume.

**Goal:** Run controlled length/placement study on the teammate's exact88tasks.
**Architecture:** New experiments/fixed_carrier_study uses original native runtime and
scorer, preauthored domain stimuli, existing immutable RunStore, its own schema/driver.
**Tech Stack:** Python,unittest,AutoGen0.7.5,OpenAI3.26,Ollama35B/8B,tmux.
**Spec:** docs/superpowers/specs/2026-10-26-fixed-carrier-study-design.md

## Global Constraints
- Full880cells,exact88IDs,3codes6/11/17×3positions,clean1,trial1,B3,maxturns12.
- Original actor/judge/temp/context/retry behavior and score_run untouched.
- Frozen preauthored seed stimulus is NOT a model output; genuine peer model execution.
- Pilot20is a formal subset, not separate repeated attempts; full resumes after audit.
- No success screening/restarts/scorer redesign; all failures retained.
- GPU0only,owned-service lifecycle,tmux,strict source/data/config/hash identity.

## Review Focus
- Pinned88task identity and equal denominators never silently reduced.
- Controlled seed bypass happens exactly once only for attacked seed,never peers/clean.
- Same carrier bytes at allpositions; tool/history order and seedview preserved.
- All original scorer fields kept; newdiagnostics never relabel legacy/gold metrics.
- Pilot/full continuation skips all started keys, stops on transport/config failures.

### Task1: Frozen catalog,manifest,thin native adapter,driver/audit
- [x] Tests RED for15carrier roundtrips,880keys/88IDs/pilot20subset,byte matching,
  seed bypass/realpeer/clean routing,restore onfailure,scorer passthrough and resume.
- [x] Implement catalog.py,study.py,runner.py,cli.py + README; reuse existing storage.
- [x] Tests GREEN and full suite; one fresh reviewer; one RED/GREEN fix pass; commit.

### Task2: Original model preparation and20pilot
- [x] Download original8B if missing with CPU-only private service; stop after download.
- [x] Metadata preflight/version/UUID verification; freeze local+remote880plan.
- [x] tmux pilot20using880manifest; monitor exact events; no positive-outcome gate.
- [x] Audit pilot; preserve20for formal continuation; no unwanted model/scorerchanges.

### Task3: Formal continuation and deliverables
- [x] Start remaining860onlyafter mechanicalpilot gate and same frozen identity.
- [ ] Detached controller writes reports/audits and stops owned model, releasesGPU.
- [ ] Verify880terminal/88percondition or report incompleteness, download all evidence,
  Chinese report/Englishtables/allnativefields; no false full completion claim.

## Ledger
Base0327141;existing linked worktree feat/teammate-final retained.
Pre-flight:original native run_task and RunStore/report share task/cell metadata;
newdriver uses new schema but the same key fields. Pilot is an ordered subset only.
Ruling: controlled first seed message uses an explicit synthetic CreateResult with
0usage and model_generated=false; downstream model behavior stays real. This avoids
calling a generator then discarding its output or scoring a transcript unlike inputs.
Ruling: generic REVIEWTASKS/REVIEWTASKDETAILS aliases chosen for all5domains;5domain
covertexts preauthored, not per-query generation. This isolates the new study scope.
Ruling: memory is system authority, separate comparison. Native metricbugs retained
and reported per user's instruction, no extra semanticjudge/gold claim.

Task1: initial11new tests passed. Fresh review /root/review_fixed_study found2P1s:
pre-execution pilot/prior-failure gate missing; audit trusting placement flags instead
of real input/output evidence. Both reproduced RED then fixed. Actual original and
forwarded actor inputs now retained and independently compared, real actor/judge I/O
counts/categories checked, zero-evidence/wrong-position/missing-query/peer/output
probes reject. Formal stage requires fresh20pilot audit; failed/interrupted/invalid
existing rows block all automatic new claims, including resumed pilot.
Full suite before review126; after fix130tests targeted for final verification.
Declined judgments recorded: model efficacy, naturalness/semantic gold, historical
model behavior remain unverified; model lifecycle and real pilot are next, not inferred.
Prefetch complete2026-10-26T16:54:31Z,CPU-only/noinference,originalqwen3:8b cached,
privateprefetch service exited. No model substitution/paid API.

Final tests130/130 before commit1e09f49. Local/remote fullplan SHA identical:
fd5f42a7c7f9e5f870f1fb4f200f8673dd0cdddcff804c7c5fa85153cc6d4fd9.
Task2 in progress:tmux controller472615/ownOllama472630,UTC17:17:51start,GPU0only.
At17:20:29UTC 1clean completed,actual actor/judge events pass independent read-only
inspection; first attack running. No claim that20pilot or880formal finished.
Background controller enforces pilot/audit thenremaining860,strict formalgate;
heartbeat fixed-carrier-88-task-study-follow-up tracks completion/errors quietly.
Results snapshot/paths at docs/results/2026-10-26-fixed-carrier-study-progress.md.

Task2 complete:pilot20 passed19:22:45UTC,issues=[];controller automatically resumed
remaining860under same fd5f42...manifest.19:24:12UTC21/880completed,actualI/Oclean.
Pilot-only closed evidence downloaded(20keys,694368bytes,SHA256
ebd7b84b1f687d6022a29490fb806e3cef8191e03e860d68aab0de232808f321),
local offline design/codehash/pilot audit all pass. No model requests for this check.
Task3 in progress; no formal completion/efficacy claim. Automation prompt updated to
formal stage, unchanged schedule/notification policy. No duplicate launch/attempts.
