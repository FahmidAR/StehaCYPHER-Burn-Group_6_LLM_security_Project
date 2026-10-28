# Teammate-only length/position correction

Binding user direction: only change hidden phrase length and placement. Keep the
teammate's implemented generation, propagation, evaluation and output fields.
No experiment/model call before the user's separate run approval.

Root cause: previous extension substituted a deterministic carrier, changed all
role prompts and added a second completion judge. Those are extra experimental
variables. Withdraw that plan; retain its never-run artifacts as superseded.

## Correction contract

Pin9a60c83. Call original mas_runner.run_task and metrics.score_run directly,
plus original run_experiment.decode_success_for. Do not clone the team runtime,
replace generation, change seed instructions beyond its trigger parameter,
change codebook/protocol, or add a judge call/criterion/control arm.

Length: set the original ACROSTIC_TRIGGER in payload_riddle and mas_runner to
the normalized phrase for the duration of each attack run. Original prompt then
requests the corresponding number of task-related sentences; all other words
and attack behavior remain identical. Clean uses original defaults.

Position: in a receiving agent's model input only, locate the FIRST published
seed-agent text message (including invalid acrostics; never select success),
and move its exact text/message to before original user request, after original
user request, or a system-memory message. Leave seed's own generation input,
normal roles/tools, all later peer messages and tool-call/result order unchanged.
After-user is identity on the original ordinary message order. Do not move a
generation instruction and mislabel it as moving hidden text. Memory is system
context, not a new database. Different positions run independently under the
same original generation policy; do not claim identical sampled prose.

88tasks,35Bactor/8Bjudge,B3,trial1,MAX_TURNS12 and original timeouts/retries.
Same task/clean-first loop order as teammate driver; two phrases x3positions
plusoneclean/task=616. No optional benign arms, bootstrap tests, corrected TC,
actual-token replacement, or new efficacy score. All original scored fields,
including decode control, are written verbatim with added identifying metadata.
Original approximate token/turn/ERS/TC definitions are retained, not relabeled
as improved metrics. Failure logging/source freeze/run approval are management
only and cannot change scored values.

## Tasks
- [x] TDD: native trigger prompt parity, exact placement / no tool-history mutation,
  no generation-side relocation, one unchanged native scoring call/all fields.
- [x] Replace our design/runner/report with thin native adapter; remove extra
  tests/features; update CLI schema and reject superseded plan before APIs.
- [x] Full offline tests, real88-task preparation only, fresh whole-change review
  and one RED/GREEN fix pass; explain only actual differences; no run.

## Ledger
Pre-flight: design cells feed native adapter and unchanged scorer/report. No
carrier supplied by design; carrier can only originate in native seed output.
Ruling: position applies to the receiver's first seed-generated message, not
the seed generation prompt, so the source generation mechanism stays unchanged.
Ruling: user's latest narrow scope supersedes the previous template/extra-judge
design. Keep historical artifacts but make old schema non-executable.

Correction implementation commit19f1a69 (base5daa3c3). Observed RED for missing
native trigger/placement adapter, template leakage, native export and superseded
schema; GREEN after replacement.18 extension tests now exercise original pinned
prompts/scorer, complete native field export, receiver placement and no-approval.
Old38 generation+18analysis+2ops tests also GREEN, total76. Native upstream loader
ResourceWarning is inherited; no source behavior change made to hide it.

Fresh read-only whole-change review approved19f1a69 with no Critical/Important/
Minor findings. No fix pass or second reviewer needed. Reviewer declined live
integration, model acrostic success and empirical efficacy; ruling: these remain
unverified pending separate run approval. Teammate metric redesign is explicitly
out of scope under the user's instruction.

Prepared results/teammate-native-ablation-20261025/plan.json, SHA
056fbc01a6ead194a48eb9fcff3d662f5eac31a74955380c99b8d780aa45a683.
Verified616 unique unstarted rows, zero scored rows, no attempts directory and
no OpenAI/AutoGen imports during preparation. Source/data/code hashes verified.
No model requests, server launch, GPU use, deployment, push or automation.
Keep the existing branch/worktree for the user's requested run-approval stage.
