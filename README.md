# StegaCIPHER-Burn

Task-Aligned Denial-of-Collaboration attacks on LLM multi-agent systems from hidden
or stealthy input — **Group 6** (Fahmid Al Rifat, Yinhao Wu, Danhua Zhao).

**STEGA**nography · task **ALIGN**ment · token **BURN**

An attacker turns a multi-agent team's own benign task into an exponentially growing
"validation" that never finishes — degrading task completion and burning 2–4x the
tokens, while every message still looks like diligent on-task work. The coordinating
signal can be hidden in the chat via a steganographic covert channel.

## Repository layout

All project code and materials are in [`stegacipher-burn/`](stegacipher-burn/):

- `src/` — the pipeline: TAMAS task loader + filter, per-agent tool wiring, the
  task-aligned riddle payload, the multi-agent runner, metrics (completion, tokens,
  P-ASR/PTN, stealth, tool-grounded), the steganography methods and the agent-decode
  experiment.
- `scripts/` — SLURM job scripts for the GPU cluster.
- `docs/` — how the steganography works.
- `results/` — result data (`*.jsonl`) and summary tables.
- `slides/` — the presentation (`StegaCIPHER-Burn.pptx`).
- `data/README.md` — how to obtain the TAMAS dataset (external; not committed).

See [`stegacipher-burn/README.md`](stegacipher-burn/README.md) for details.
