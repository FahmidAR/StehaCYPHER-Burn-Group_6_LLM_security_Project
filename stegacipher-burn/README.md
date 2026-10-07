# StegaCIPHER-Burn

Covert, task-aligned Denial-of-Collaboration attack on LLM multi-agent systems, with
a full effectiveness / cost / stealth evaluation. Builds on CORBA; this repo is the
Week-7 evaluation design, implemented as **version 1**.

## v1 choices (one of each, per the design doc)
- **Dataset:** TAMAS (`data/TAMAS`, microsoft/TAMAS). We use its *benign* tasks —
  the agent roster + the benign clause of each `user query` (injected text stripped).
  Loader: `src/tamas_loader.py`.
- **Input encoding:** Method A — lexical / synonym-substitution text stego.
  Codec + round-trip + capacity: `src/stego_codec.py`.
- **Payload:** task-aligned exponential riddle (branching factor parameterized) that
  turns the team's own task into exhaustive "test-case" validation busywork while
  every message reads as on-task. `src/payload_riddle.py`.
- **Metrics (all):** decode-success, task-completion (LLM-judge), completion-time
  (turns), token usage, P-ASR, PTN, stealth-similarity (LLM-judge). ERS = stub
  (needs TAMAS's own scorer). `src/metrics.py`.

## Run
```
sbatch scripts/run_stega_coe.sbatch      # serves qwen3.5:35b, runs clean vs attacked
```
Outputs: `results/v1_results.jsonl` (per-run scores) + a clean-vs-attacked summary
table in `results/v1_console.log`.

## Pipeline
`run_experiment.py` -> for each benign task: run CLEAN and ATTACKED
(`mas_runner.run_task`) -> score with `metrics.score_run` -> summary table.

## Planned later variations (not in v1)
- Method B text stego (generative/arithmetic-coded); image/audio modalities.
- Live agent-side decode of the covert channel (v1 validates the codec standalone).
- Defenses: CORBA's 3 baselines + a steganalysis detector + CRPB (ours).
- MARBLE/MultiAgentBench secondary corpus for cross-topology results.
- TAMAS ERS wired into `metrics.score_run`.
