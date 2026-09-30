from __future__ import annotations

"""BPO baseline: Black-box Prompt Optimization (arXiv:2311.04155, thu-coai/BPO).

Drop-in replacement for engine/ensemble_pair_gen.py's generate_candidate() --
same output contract, {"good_prompt": str, "reasoning": str} -- but BPO is a
single fixed Llama-2-7B checkpoint (baselines/bpo_model/), not this project's
generator ensemble, and it never looks at the skill/trace/intent context that
generate_candidate() is given. It only ever sees the raw bad_prompt text, per
the paper's own template. That's the whole point of it as a baseline: it's
the "generic prompt-safety rewriter with zero skill-specific signal" point of
comparison.

This script only PRODUCES candidates. It does not run them through the
sandbox or the judge ensemble -- that requires the Ollama + sandbox stack
that lives on the other server (see conversation). Output is written in a
subset of engine/ensemble_pair_gen.py's PAIR_COLS schema so it drops straight
into that pipeline's judging step without reshaping.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "bpo_model"
DEFAULT_MANIFEST = REPO_ROOT / "datasets" / "harmful_executed" / "manifest.csv"

# Exact template from the BPO model card / paper -- not our wording, theirs.
BPO_TEMPLATE = (
    "[INST] You are an expert prompt engineer. Please help me improve this "
    "prompt to get a more helpful and harmless response:\n{prompt} [/INST]"
)

# Subset of engine/ensemble_pair_gen.py PAIR_COLS -- judge/verdict columns
# are left blank for the downstream sandbox+judge run to fill in.
PAIR_COLS = [
    "ts", "skill", "bad_prompt", "winning_generator_model", "good_prompt",
    "harm_judge_votes", "harm_unanimous_pass", "intent_judge_votes", "intent_unanimous_pass",
    "passed", "detail_json_path",
]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_bad_prompts(manifest_path: Path, dataset: str, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    with open(manifest_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if dataset and row.get("dataset", "").strip().upper() != dataset.upper():
                continue
            bad_prompt = (row.get("bad_prompt") or "").strip()
            if not bad_prompt:
                continue
            items.append({"skill": row["skill"], "bad_prompt": bad_prompt})
    if limit > 0:
        items = items[:limit]
    return items


class BPORewriter:
    """Loads the checkpoint once; supports the paper's optional iterative mode
    (feed output back in as input, up to N times -- Sec. 5.3, diminishing
    returns reported after ~4 rounds)."""

    def __init__(self, model_dir: Path, device: str | None = None, dtype: str = "auto") -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        torch_dtype = torch.float16 if (dtype == "auto" and device == "cuda") else torch.float32
        print(f"[bpo] loading {model_dir} on {device} (dtype={torch_dtype})", file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = AutoModelForCausalLM.from_pretrained(str(model_dir), torch_dtype=torch_dtype)
        self.model.to(device)
        self.model.eval()

    def rewrite_once(self, prompt: str, *, max_new_tokens: int, temperature: float, top_p: float) -> str:
        text = BPO_TEMPLATE.format(prompt=prompt)
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 1e-5),
                top_p=top_p,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        gen_ids = out[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    def rewrite(self, prompt: str, *, iterations: int, max_new_tokens: int,
                temperature: float, top_p: float) -> dict[str, Any]:
        history = [prompt]
        current = prompt
        for _ in range(max(iterations, 1)):
            nxt = self.rewrite_once(current, max_new_tokens=max_new_tokens,
                                     temperature=temperature, top_p=top_p)
            if not nxt:
                break
            history.append(nxt)
            current = nxt
        return {"good_prompt": current, "reasoning": "", "history": history}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--dataset", default="D1", help="manifest 'dataset' column filter, empty string = all")
    ap.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "out" / "bpo"))
    ap.add_argument("--limit", type=int, default=0, help="0 = no cap")
    ap.add_argument("--iterations", type=int, default=1, help="BPO paper's iterative mode; 1 = single pass")
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--device", default=None)
    return ap


def main() -> None:
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest)
    out_dir = Path(args.out_dir)
    details_dir = out_dir / "details"
    details_dir.mkdir(parents=True, exist_ok=True)

    items = load_bad_prompts(manifest_path, args.dataset, args.limit)
    if not items:
        print(f"no bad_prompt rows found in {manifest_path} for dataset={args.dataset!r}", file=sys.stderr)
        sys.exit(1)
    print(f"[bpo] {len(items)} skill(s) to rewrite", file=sys.stderr)

    rewriter = BPORewriter(Path(args.model_dir), device=args.device)

    csv_path = out_dir / "pairs_bpo.csv"
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PAIR_COLS)
        if write_header:
            writer.writeheader()

        for i, it in enumerate(items, 1):
            skill, bad_prompt = it["skill"], it["bad_prompt"]
            t0 = time.time()
            try:
                result = rewriter.rewrite(
                    bad_prompt, iterations=args.iterations,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature, top_p=args.top_p,
                )
            except Exception as exc:
                print(f"[bpo] {i}/{len(items)} {skill}: FAILED ({exc})", file=sys.stderr)
                continue
            dt = time.time() - t0
            print(f"[bpo] {i}/{len(items)} {skill}: {dt:.1f}s, "
                  f"{len(result['history'])-1} round(s)", file=sys.stderr)

            detail_path = details_dir / f"{skill}.json"
            detail_path.write_text(json.dumps({
                "ts": now_iso(), "skill": skill, "bad_prompt": bad_prompt,
                "method": "bpo_baseline", "model_dir": str(args.model_dir),
                "iterations_requested": args.iterations,
                "generation_params": {
                    "max_new_tokens": args.max_new_tokens,
                    "temperature": args.temperature, "top_p": args.top_p,
                },
                "history": result["history"],
                "good_prompt": result["good_prompt"],
                "wall_seconds": dt,
            }, indent=2, ensure_ascii=False), encoding="utf-8")

            writer.writerow({
                "ts": now_iso(), "skill": skill, "bad_prompt": bad_prompt,
                "winning_generator_model": "bpo_baseline",
                "good_prompt": result["good_prompt"],
                "harm_judge_votes": "", "harm_unanimous_pass": "",
                "intent_judge_votes": "", "intent_unanimous_pass": "",
                "passed": "", "detail_json_path": str(detail_path),
            })
            f.flush()

    print(f"[bpo] done. candidates: {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
