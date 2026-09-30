from __future__ import annotations

"""PromSec baseline (CCS 2024, arXiv:2409.12699, github.com/mahmoudkanazzal/PromSec).

Runs the RELEASED PromSec pipeline, unmodified in algorithm, against every
skill in datasets/harmful_executed/manifest.csv (d1+d2+d3). This ports the
public repo's Demo notebook's vet_code() (cell 32) into a standalone script,
swapping the notebook's hardcoded OpenAI "gpt-4o" calls for an OpenAI-SDK
client pointed at an Ollama server (qwen3.5:35b), since that's the model
this project's own pipeline uses. No other part of PromSec's algorithm is
touched.

IMPORTANT CAVEATS (read before trusting these numbers as representative of
the PromSec paper's real results):

1. PromSec's native mode operates on PYTHON code (ast.parse(ci)) -- it has
   no notion of prompts. It is being used here in its own intended mode:
   "clean vulnerabilities out of this code", applied to each skill's own
   shipped script. That is a DIFFERENT comparison axis than this project's
   prompt-rewriting ("route around the skill via the prompt") -- see
   conversation for the full discussion. Skills without Python source
   (the large majority of d1 and d3, ~half of d2) are recorded as
   status=not_applicable_non_python, not silently dropped.

2. utils_new.py's generate_cfg_from_code() calls build_cfg_from_ast(tree, cfg)
   with tree the whole ast.Module -- but build_cfg_from_ast() only branches
   on isinstance(node, ast.stmt) or isinstance(node, list), and a Module is
   neither, so that call always silently no-ops: the CFG comes back with
   zero nodes for every possible Python input, unconditionally (not
   content-dependent -- verified directly). That makes the released pipeline
   produce literally nothing for 100% of applicable skills, not merely a
   weak signal. This is a wrong-argument bug, not an algorithm/design
   choice -- build_cfg_from_ast's own recursive calls already pass
   node.body for If/For/While, so the top-level call should too. Fixed
   locally in this script's generate_cfg_from_code() (passes tree.body),
   nowhere else, and the vendor repo under baselines/PromSec/ is untouched.

3. Even with (2) fixed, get_node_features() in utils_new.py still reads
   node attributes ("contains_function", "contains_loop", "contains_if",
   "contains_comment") that build_cfg_from_ast() never sets (it only ever
   sets ast_node=node) -- so every node's 4-d feature vector is still
   structurally constant [0,0,0,0] regardless of real per-statement content.
   That part is DELIBERATELY left as released, not patched: deciding what
   "contains_comment" should mean, or how to derive the other three from
   ast_node's real type, is an algorithmic-fidelity judgment call, not a
   wrong-argument bug like (2), and the released pretrained checkpoints
   (in_feats=1) are shape-consistent with this exact flattening/encoding
   scheme either way. With (2) fixed, the CFG topology (which statements
   exist and how control flows between them) is now real; only the per-node
   TYPE feature is still flat. Whatever security-improvement shows up in
   the CWE before/after counts should be attributed mostly to the LLM
   refinement step's explicit security instructions and the now-real graph
   topology/size, not to node-level type discrimination.

This script only produces before/after code + CWE counts. It does not touch
this project's own sandbox/judge ensemble.
"""

import argparse
import ast
import csv
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMSEC_DIR = Path(__file__).resolve().parent / "PromSec"
DEFAULT_MANIFEST = REPO_ROOT / "datasets" / "harmful_executed" / "manifest.csv"
DATASETS_ROOT = REPO_ROOT / "datasets" / "harmful_executed"

sys.path.insert(0, str(PROMSEC_DIR))
from utils_new import get_node_features  # noqa: E402
from utils_new import build_cfg_from_ast  # noqa: E402


def generate_cfg_from_code(file_path: str):
    """utils_new.py's own generate_cfg_from_code() calls
    build_cfg_from_ast(tree, cfg) with tree the whole ast.Module node.
    build_cfg_from_ast() only branches on isinstance(node, ast.stmt) or
    isinstance(node, list) -- a Module is neither, so that call always
    silently no-ops and the CFG comes back with zero nodes for every
    possible Python input, unconditionally (verified directly: `isinstance
    (ast.parse(code), ast.stmt)` and `isinstance(ast.parse(code), list)`
    are both False for every module). Not a design choice, a wrong-argument
    bug -- it should pass tree.body (the list of top-level statements) the
    way build_cfg_from_ast's own recursive calls do for If/For/While bodies.
    Fixed here, only here, in our own script rather than editing the vendor
    repo's utils_new.py. See this script's module docstring caveat (2) for
    what is deliberately left unfixed."""
    import networkx as nx
    with open(file_path, "r") as f:
        code = f.read()
    tree = ast.parse(code)
    cfg = nx.DiGraph()
    build_cfg_from_ast(tree.body, cfg)
    return cfg

MANIFEST_COLS = [
    "skill", "dataset", "status", "source_file",
    "cwe_count_before", "cwe_list_before",
    "cwe_count_after", "cwe_list_after",
    "detail_json_path", "error",
]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ===========================================================================
# get_completion -- notebook cell 8, retargeted from OpenAI to Ollama's
# OpenAI-compatible endpoint. Same call shape, same return contract.
# ===========================================================================

def make_get_completion(base_url: str, model: str, timeout: int = 1800):
    """Same call contract as the notebook's get_completion(prompt, model) ->
    str, just against Ollama's NATIVE /api/chat instead of the OpenAI-SDK
    client. Ollama's OpenAI-compatible /v1/chat/completions shim silently
    ignores "think": false (verified directly: identical trivial prompt,
    651 reasoning+completion tokens / 7s via /v1, vs 16 tokens / 1.1s via
    /api/chat with think:false) -- qwen3.5:35b is a reasoning model whose
    unthrottled chain-of-thought made even a single vet_code() call exceed
    a 600s client timeout on a real skill's AST-dump-sized prompt. Disabling
    "thinking" is a transport/infra choice (which endpoint + one HTTP flag),
    not a change to PromSec's prompts or algorithm -- and it's arguably
    MORE faithful to the paper, which was built against GPT-3.5/gpt-4o,
    non-reasoning models with no hidden chain-of-thought to begin with."""
    import requests
    api_base = base_url.rstrip("/")
    if api_base.endswith("/v1"):
        api_base = api_base[: -len("/v1")]
    chat_url = f"{api_base}/api/chat"

    def get_completion(prompt: str, model_override: str | None = None) -> str:
        resp = requests.post(chat_url, json={
            "model": model_override or model,
            "messages": [{"role": "user", "content": prompt}],
            "think": False,
            "stream": False,
            "options": {"temperature": 0},
        }, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    return get_completion


# ===========================================================================
# Generator -- notebook cell 19, verbatim (only what vet_code() needs;
# Discriminator is training-only, not used at inference time).
# ===========================================================================

def build_generator():
    import torch.nn as nn
    import torch_geometric.nn as pyg_nn

    in_feats, hidden_feats, out_feats = 1, 128, 1

    class Generator(nn.Module):
        def __init__(self, in_feats, hidden_feats, out_feats):
            super().__init__()
            self.conv1 = pyg_nn.GraphConv(in_feats, hidden_feats)
            self.conv2 = pyg_nn.GraphConv(hidden_feats, out_feats)
            self.relu = nn.ReLU()

        def forward(self, x, edge_index):
            x = self.conv1(x, edge_index)
            x = self.relu(x)
            embeddings_before = self.conv2(x, edge_index)
            updated_x = self.relu(embeddings_before)
            return embeddings_before, updated_x

    return Generator(in_feats, hidden_feats, out_feats)


# ===========================================================================
# calculate_vcs -- notebook cell 21, verbatim except a per-call unique temp
# file (the original hardcodes "temp_code.py", unsafe for anything but a
# single sequential notebook cell).
# ===========================================================================

def calculate_vcs(code: str, scratch_dir: Path) -> tuple[int, list[str]]:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    code_filename = scratch_dir / f"vcs_{uuid.uuid4().hex}.py"
    code_filename.write_text(code, encoding="utf-8")
    try:
        command = f"bandit -f json {code_filename}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        try:
            result_json = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 0, []
        cwe_set = set()
        for issue in result_json.get("results", []):
            cwe = issue.get("issue_cwe", {})
            if "id" in cwe:
                cwe_set.add(cwe["id"])
        return len(cwe_set), sorted(cwe_set)
    finally:
        code_filename.unlink(missing_ok=True)


# ===========================================================================
# graph_to_code / remove_markdown -- notebook cell 12, verbatim except the
# model default and using our get_completion.
# ===========================================================================

def remove_markdown(code: str) -> str:
    match = re.search(r"^```python\n((.|\s)*)```$", code)
    if match:
        return match.group(1)
    return code


def graph_to_code(get_completion, original_code: str, original_ast: ast.AST,
                   original_cfg, updated_cfg, model: str) -> str:
    prompt = (
        "You are a coding assistant. Given an original Python code, its AST, the original CFG, and an updated CFG, "
        "generate an updated version of the code that maintains functionality but aligns with the updated CFG structure. "
        "Adjust control structures like loops and conditionals as needed.\n\n"
        f"Original Code:\n{original_code}\n\n"
        f"Original AST:\n{ast.dump(original_ast, annotate_fields=True, include_attributes=True)}\n\n"
        f"Original CFG:\n{str(original_cfg)}\n\n"
        f"Updated CFG:\n{str(updated_cfg)}\n\n"
        "Provide the updated Python code."
    )
    try:
        return get_completion(prompt, model).strip()
    except Exception as exc:
        print(f"[promsec] graph_to_code error: {exc}", file=sys.stderr)
        return original_code


# ===========================================================================
# vet_code -- notebook cell 32, ported to a standalone function. Same steps,
# same prompt text, only the model id and get_completion source changed.
# ===========================================================================

def vet_code(get_completion, generator, ci: str, file_path: Path, model: str,
              scratch_dir: Path) -> dict[str, Any]:
    import numpy as np
    import torch
    import networkx as nx
    from sklearn.preprocessing import LabelEncoder
    from torch_geometric.data import Data

    cfg = generate_cfg_from_code(str(file_path))
    if cfg is None or not cfg.nodes():
        raise ValueError("empty CFG")

    node_features = [get_node_features(cfg, node) for node in cfg.nodes()]
    adj_matrix = nx.adjacency_matrix(cfg).toarray()

    node_features = np.array(node_features)
    num_nodes = len(node_features)
    node_features = node_features.reshape(num_nodes, -1)
    x_list = [item for sublist in node_features for item in sublist]
    encoded_labels = LabelEncoder().fit_transform(x_list)
    encoded_labels = torch.tensor(encoded_labels, dtype=torch.float32).unsqueeze(1)

    rows, cols = np.nonzero(adj_matrix)
    edge_index = torch.tensor([rows, cols], dtype=torch.long)

    pyg_data = Data(x=encoded_labels, edge_index=edge_index)

    def extract_graph_from_pyg_data(pd):
        g = nx.Graph()
        g.add_nodes_from(range(pd.x.size(0)))
        g.add_edges_from(pd.edge_index.t().tolist())
        return g

    g_before = extract_graph_from_pyg_data(pyg_data)
    cwe_before, cwe_list_before = calculate_vcs(ci, scratch_dir)

    x, edge_index_t = pyg_data.x, pyg_data.edge_index
    embeddings_before, updated_x = generator(x, edge_index_t)

    g_after = extract_graph_from_pyg_data(Data(x=updated_x, edge_index=edge_index_t))
    original_ast = ast.parse(ci)
    ci_hat = graph_to_code(get_completion, ci, original_ast, g_before, g_after, model)
    ci_hat = remove_markdown(ci_hat)

    prompt_inv1 = (
        "Estimate a detailed prompt that could be given to ChatGPT to generate the following Python code "
        "making sure that the code generated is secure and maintains the same functionality of the code:\n"
    )
    p0 = (prompt_inv1 + "[" + ci_hat + "]. Try to be as specific as possible. The prompt must assure that the "
          "code must be in Python, not any other language.")
    p0 = p0 + " Do not provide any explanatory text, marks, or comments. Only give the prompt requested."

    estimated_prompt = get_completion(p0, model)
    p_inext = estimated_prompt + ". Do not put any explanatory text, marks, or comments. Only give the source code as a response."
    p_inext = ("In your code generation, ensure that sensitive information (secret keys, passwords) "
               "is stored in environment variables not hard-coded.") + p_inext

    codei_vetted = get_completion(p_inext, model)
    codei_vetted = remove_markdown(codei_vetted)

    cwe_after, cwe_list_after = calculate_vcs(codei_vetted, scratch_dir)

    return {
        "ci_hat": ci_hat, "estimated_prompt": estimated_prompt, "codei_vetted": codei_vetted,
        "cwe_count_before": cwe_before, "cwe_list_before": cwe_list_before,
        "cwe_count_after": cwe_after, "cwe_list_after": cwe_list_after,
    }


# ===========================================================================
# Skill resolution -- find the shipped script for a manifest row.
# ===========================================================================

def find_skill_dir(skill: str, dataset: str) -> Path | None:
    d = DATASETS_ROOT / dataset.lower() / skill
    return d if d.is_dir() else None


def find_python_source(skill_dir: Path) -> Path | None:
    py_files = sorted(skill_dir.rglob("*.py"), key=lambda p: p.stat().st_size, reverse=True)
    return py_files[0] if py_files else None


def dominant_extension(skill_dir: Path) -> str:
    from collections import Counter
    exts = Counter(p.suffix.lstrip(".") or "(none)" for p in skill_dir.rglob("*") if p.is_file())
    return exts.most_common(1)[0][0] if exts else "(empty)"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent / "out" / "promsec"))
    ap.add_argument("--ollama-base-url", required=True, help="e.g. http://h100-8s-05:11434/v1")
    ap.add_argument("--model", default="qwen3.5:35b")
    ap.add_argument("--limit", type=int, default=0, help="0 = no cap")
    ap.add_argument("--checkpoint", default=str(PROMSEC_DIR / "trained_generator_model.pt"))
    return ap


def main() -> None:
    args = build_parser().parse_args()
    import torch

    out_dir = Path(args.out_dir)
    details_dir = out_dir / "details"
    scratch_dir = out_dir / "_scratch"
    details_dir.mkdir(parents=True, exist_ok=True)

    print(f"[promsec] loading generator checkpoint from {args.checkpoint}", file=sys.stderr)
    generator = build_generator()
    generator.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=False))
    generator.eval()

    get_completion = make_get_completion(args.ollama_base_url, args.model)

    rows = list(csv.DictReader(open(args.manifest, newline="", encoding="utf-8")))
    if args.limit > 0:
        rows = rows[: args.limit]
    print(f"[promsec] {len(rows)} skill(s) in manifest", file=sys.stderr)

    csv_path = out_dir / "results_promsec.csv"
    write_header = not csv_path.exists()
    counts = {"applicable": 0, "not_applicable_non_python": 0, "skill_dir_missing": 0, "error": 0}

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if write_header:
            writer.writeheader()

        for i, row in enumerate(rows, 1):
            skill, dataset = row["skill"], row["dataset"]
            skill_dir = find_skill_dir(skill, dataset)
            base_row = {"skill": skill, "dataset": dataset, "detail_json_path": "", "error": ""}

            if skill_dir is None:
                counts["skill_dir_missing"] += 1
                writer.writerow({**base_row, "status": "skill_dir_missing", "source_file": "",
                                  "cwe_count_before": "", "cwe_list_before": "",
                                  "cwe_count_after": "", "cwe_list_after": ""})
                print(f"[promsec] {i}/{len(rows)} {skill}: skill dir missing", file=sys.stderr)
                continue

            py_source = find_python_source(skill_dir)
            if py_source is None:
                counts["not_applicable_non_python"] += 1
                writer.writerow({**base_row, "status": "not_applicable_non_python",
                                  "source_file": dominant_extension(skill_dir),
                                  "cwe_count_before": "", "cwe_list_before": "",
                                  "cwe_count_after": "", "cwe_list_after": ""})
                print(f"[promsec] {i}/{len(rows)} {skill}: not applicable (no .py, "
                      f"dominant ext={dominant_extension(skill_dir)})", file=sys.stderr)
                continue

            t0 = time.time()
            try:
                ci = py_source.read_text(encoding="utf-8")
                result = vet_code(get_completion, generator, ci, py_source, args.model, scratch_dir)
            except Exception as exc:
                counts["error"] += 1
                writer.writerow({**base_row, "status": "error", "source_file": str(py_source),
                                  "cwe_count_before": "", "cwe_list_before": "",
                                  "cwe_count_after": "", "cwe_list_after": "", "error": str(exc)[:300]})
                print(f"[promsec] {i}/{len(rows)} {skill}: ERROR ({exc})", file=sys.stderr)
                continue

            dt = time.time() - t0
            counts["applicable"] += 1
            detail_path = details_dir / f"{skill}.json"
            detail_path.write_text(json.dumps({
                "ts": now_iso(), "skill": skill, "dataset": dataset, "method": "promsec_baseline",
                "model": args.model, "source_file": str(py_source),
                "original_code": ci, "wall_seconds": dt, **result,
            }, indent=2, ensure_ascii=False), encoding="utf-8")

            writer.writerow({
                "skill": skill, "dataset": dataset, "status": "applicable", "source_file": str(py_source),
                "cwe_count_before": result["cwe_count_before"], "cwe_list_before": json.dumps(result["cwe_list_before"]),
                "cwe_count_after": result["cwe_count_after"], "cwe_list_after": json.dumps(result["cwe_list_after"]),
                "detail_json_path": str(detail_path), "error": "",
            })
            f.flush()
            print(f"[promsec] {i}/{len(rows)} {skill}: {dt:.1f}s, "
                  f"CWE {result['cwe_count_before']}->{result['cwe_count_after']}", file=sys.stderr)

    print(f"[promsec] done. {counts}. results: {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
