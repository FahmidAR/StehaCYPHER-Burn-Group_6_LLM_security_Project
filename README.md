# StehaCYPHER-Burn-Group_6_LLM_security_Project

Baseline comparison work for [PromSkillGuardian](https://github.com/FahmidAR/PromSkillGuardian): evaluating two
published prompt/code-rewriting methods against the same malicious-agent-skill dataset PromSkillGuardian is
evaluated on, as points of comparison for its own repair pipeline.

## What's here

- **`baselines/bpo_baseline.py`** — runs [BPO (Black-Box Prompt Optimization, arXiv:2311.04155)](https://arxiv.org/abs/2311.04155),
  a pretrained Llama-2-7B prompt rewriter ([THUDM/BPO](https://huggingface.co/THUDM/BPO)), against each skill's
  triggering prompt. Single fixed template, single (or N-round iterative) forward pass, no skill-specific context.
- **`baselines/promsec_baseline.py`** — runs [PromSec (CCS 2024, arXiv:2409.12699)](https://arxiv.org/abs/2409.12699)
  against each skill's own shipped Python source, using its released pretrained gGAN generator checkpoint plus an
  LLM refinement loop (ported from the [official repo](https://github.com/mahmoudkanazzal/PromSec)'s demo notebook).
- **`baselines/PromSec/`** — trimmed copy of the vendor repo: their code (`utils_new.py`, demo notebook) and
  pretrained checkpoints (`trained_generator_model.pt`, `trained_discriminator_model.pt`) only. Their own
  Training_DS/Testing_DS/Results_* folders are omitted (not our work, already public in their repo) — see the
  original repo above if you need those.
- **`baselines/out/`** — results from the runs described below.
- **`baselines/run_bpo_baseline.sbatch`**, **`baselines/serve_qwen35.sbatch`** — SLURM job scripts used to run
  these on a 1-GPU allocation (BPO) and to serve `qwen3.5:35b` via Ollama for PromSec's LLM-in-the-loop step.

Not included: the BPO checkpoint itself (~13GB, fetch with
`huggingface_hub.snapshot_download(repo_id="THUDM/BPO")`) and PromSkillGuardian's own `engine/`/`datasets/` — this
repo is the baseline-comparison layer only, meant to sit alongside a checkout of PromSkillGuardian.

## What each baseline actually measures

| | Input | Judge used here | Applies to |
|---|---|---|---|
| BPO | the skill's triggering prompt (text only, no skill context) | none yet — see "Not done yet" | all skills with a recorded triggering prompt |
| PromSec | the skill's own Python source code | Bandit CWE count, before vs. after | skills that ship Python source |

These are two different comparison axes: BPO tries to route around a skill via the prompt (same axis
PromSkillGuardian's own repair pipeline works on); PromSec tries to clean vulnerabilities out of the skill's code
itself. Neither is a strict apples-to-apples substitute for the other, or for PromSkillGuardian's own method,
without being run through the same judge (see "Not done yet" below).

## Results so far

**BPO** — ran on all 24 skills in the `d1` corpus (the only skills in the dataset with a recorded triggering
prompt; `d2`/`d3` don't have one recorded — see below). Single-pass rewrite per skill.
4/24 rewrites came back byte-identical to the input — plausible given BPO's own stated limitation (trained on
~14k generic RLHF-style prompts, not adversarial/skill-triggering ones), not a bug in the runner.

**PromSec** — ran against all 234 skills across `d1`+`d2`+`d3`:

| status | count |
|---|---|
| applicable (had Python source) | 110 |
| not applicable (no Python source — mostly bash/markdown-only skills) | 121 |
| skill directory missing | 1 |
| error (unparseable source / one call timeout) | 2 |

Of the 110 applicable skills: **48 improved** (Bandit CWE count dropped), 44 unchanged, 18 got worse.
Total CWE findings across all applicable skills: 227 → 161.

Two issues were found in the released PromSec code while wiring this up, documented in full in
`promsec_baseline.py`'s module docstring:
1. **Fixed** (in our script only, not upstream): `generate_cfg_from_code()` passed the whole `ast.Module` node to
   `build_cfg_from_ast()`, which only handles `ast.stmt`/`list` — this made the released code return an empty CFG
   for every possible input, unconditionally. This is a wrong-argument bug, not a design choice, so it's fixed
   locally (passes `tree.body` instead).
2. **Left as released**: `get_node_features()` reads node attributes that `build_cfg_from_ast()` never actually
   sets, so every node's 4-d feature vector is still structurally constant. This is a judgment call about the
   algorithm's fidelity, not a wrong-argument bug, so it was left alone and just documented — CWE improvements
   should be attributed mostly to the LLM refinement step's explicit security instructions plus the now-real graph
   topology from fix (1), not to node-level type discrimination.

PromSec's LLM-in-the-loop step originally calls OpenAI's API (`gpt-3.5-turbo`/`gpt-4o`); here it's pointed at
`qwen3.5:35b` served locally via Ollama instead (same model PromSkillGuardian's own pipeline uses as a generator),
with Ollama's `think: false` flag set — the model's default chain-of-thought reasoning made even a single call
exceed a 30-minute timeout on realistic prompts, and disabling it is arguably more faithful to the original paper
anyway, which was built against non-reasoning models.

## Not done yet

Both baselines above only produce **candidates** (a rewritten prompt / a rewritten source file). Neither has been
scored by PromSkillGuardian's own judge ensemble or run through its actual sandbox (RSA) execution — that
requires:

1. **`bad_prompt` for `d2`/`d3`.** The dataset's `manifest.csv` only has a recorded triggering prompt for `d1`'s 24
   skills; `d2` (198 skills) and `d3` (12 skills) leave it blank. Extending BPO's coverage past `d1` needs this
   harvested from a prior RSA audit run's `run_results.json` traces (same mechanism PromSkillGuardian's own
   `--bad-from-outputs` flag uses).
2. **A sandbox + judge ensemble run.** Actually verifying "does this candidate avoid the harmful behavior AND
   preserve the user's intent" requires executing each candidate against the real skill in a sandbox, then scoring
   it with PromSkillGuardian's harm/intent judge ensemble (`engine/ensemble_pair_gen.py`) — several more models
   served via Ollama plus a container runtime for isolation. This repo doesn't include that yet.
3. Note: `d4` mentioned in earlier discussion is not a separate corpus — per the dataset's own
   `datasets/harmful_executed/README.md`, it's a join over `d1`+`d2`+`d3` with no independent skills of its own.

## Reproducing

```bash
# BPO checkpoint (13GB)
python3 -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='THUDM/BPO', local_dir='baselines/bpo_model')"

# BPO run (needs a GPU)
python3 baselines/bpo_baseline.py --dataset D1 --out-dir baselines/out/bpo

# qwen3.5:35b via Ollama (needed for PromSec's LLM step)
sbatch baselines/serve_qwen35.sbatch   # publishes host:port to baselines/ollama_endpoint.txt

# PromSec run, across all datasets
python3 baselines/promsec_baseline.py --ollama-base-url http://<host-from-endpoint-file>:11434/v1 --out-dir baselines/out/promsec
```
