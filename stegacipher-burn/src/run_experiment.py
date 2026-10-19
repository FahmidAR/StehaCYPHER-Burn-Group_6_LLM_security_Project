"""StegaCIPHER-Burn v1 experiment driver.

For each benign TAMAS task, run a CLEAN baseline and an ATTACKED run
(task-aligned exponential riddle, branching_factor configurable). Score both on
the full metric suite and also report the decode-success of the Method-A stego
codec on the attacker's cover text. Writes JSONL rows + prints a summary table.

Env: NUM_TASKS, BRANCHING_FACTOR, MAX_TURNS, plus MODEL_* (see mas_runner).
"""

import asyncio
import json
import os
import statistics as st

from tamas_loader import load_benign_tasks
from mas_runner import run_task
from metrics import score_run
from payload_riddle import build_riddle_payload
import stego_codec


def decode_success_for(task, branching_factor):
    """Channel-integrity check: embed a control secret into a LONG cover (the
    task-aligned riddle text, which carries many carrier words) and verify the
    Method-A codec round-trips => decode-success. Using the long cover (not the
    short query) reflects the real attack, where the payload rides in the
    attacker's on-task messages, not a one-line query."""
    cover = build_riddle_payload(task["benign_query"], branching_factor)
    secret = "GO"  # 16-bit control payload
    stego, nbits, ok, cap = stego_codec.embed_message(cover, secret)
    back = stego_codec.extract_message(stego, nbits)
    return {"capacity_bits": cap, "need_bits": nbits,
            "fully_embedded": ok, "roundtrip_ok": back == secret}


def _already_done(out_path):
    """Return set of (task_id, attacked, bf, trial) already in the results file,
    so a resubmitted (previously timed-out) job resumes instead of redoing work."""
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            try:
                r = json.loads(line)
                done.add((r["task_id"], r["attacked"], r.get("branching_factor"), r.get("trial", 1)))
            except Exception:
                pass
    return done


async def main():
    n_tasks = int(os.environ.get("NUM_TASKS", "3"))
    # BF_LIST (comma list) sweeps branching factor for the RQ3 curve; falls back
    # to a single BRANCHING_FACTOR. Clean baseline is run once per task (bf-agnostic).
    bf_list = [int(x) for x in os.environ.get(
        "BF_LIST", os.environ.get("BRANCHING_FACTOR", "3")).split(",")]
    out_path = os.environ.get("STEGA_OUT",
        os.path.expanduser("~/research/StegaCYPHER-Burn/results/v1_results.jsonl"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    trials = int(os.environ.get("TRIALS", "1"))
    tasks = load_benign_tasks(limit=n_tasks, balanced=True)
    done = _already_done(out_path)
    print(f"loaded {len(tasks)} tasks across domains "
          f"{sorted({t['domain'] for t in tasks})}; {len(done)} runs already done (resuming)")

    rows = [json.loads(l) for l in open(out_path)] if os.path.exists(out_path) else []
    with open(out_path, "a") as f:
        for t in tasks:
            dec = decode_success_for(t, bf_list[0])
            plan = [(False, None)] + [(True, bf) for bf in bf_list]
            for attacked, bf in plan:
                for trial in range(1, trials + 1):
                    key = (t["task_id"], attacked, bf, trial)
                    if key in done:
                        continue
                    print(f"\n##### task={t['task_id']} attacked={attacked} bf={bf} trial={trial} #####")
                    try:
                        run = await run_task(t, attacked=attacked, branching_factor=(bf or bf_list[0]))
                    except Exception as e:
                        # one task timing out / hanging must NOT abort the whole batch;
                        # skip it (resumable: a resubmit retries the un-recorded task).
                        print(f"  [task SKIPPED] {type(e).__name__}: {e}")
                        continue
                    scored = score_run(run)
                    scored["branching_factor"] = bf
                    scored["trial"] = trial
                    scored["decode"] = dec
                    # save full transcript for future ERS / paper-method comparison
                    tdir = os.path.join(os.path.dirname(out_path), "transcripts")
                    os.makedirs(tdir, exist_ok=True)
                    with open(os.path.join(tdir, f"{t['task_id']}_att{int(attacked)}_bf{bf}_t{trial}.json"), "w") as tf:
                        json.dump({"task_id": t["task_id"], "attacked": attacked, "bf": bf,
                                   "trial": trial, "transcript": run["transcript"]}, tf)
                    rows.append(scored)
                    f.write(json.dumps(scored) + "\n")
                    f.flush()
                    print("SCORED", json.dumps({k: scored.get(k) for k in
                          ("task_id", "attacked", "branching_factor", "task_completion",
                           "p_asr", "completion_time_turns", "token_usage", "stealth_sim")}))

    # summary: clean vs attacked
    def agg(attacked, key):
        xs = [r[key] for r in rows if r["attacked"] == attacked and r.get(key) is not None]
        return (round(st.mean(xs), 3) if xs else None)

    def tc_rate(subset):
        comp = [r["task_completion"] for r in subset if "task_completion" in r]
        return round(sum(comp) / len(comp), 2) if comp else None

    def mean_of(subset, key):
        xs = [r[key] for r in subset if r.get(key) is not None]
        return round(st.mean(xs), 3) if xs else None

    print("\n==================== StegaCIPHER-Burn SUMMARY (RQ3 curve) ====================")
    print(f"tasks={len({r['task_id'] for r in rows})}  model={os.environ.get('MODEL_NAME')}")
    hdr = ["Condition", "TaskCompletion", "P-ASR", "CompletionTurns", "Tokens", "StealthSim"]
    print(" | ".join(hdr))
    clean = [r for r in rows if not r["attacked"]]
    print(" | ".join(map(str, ["Clean baseline", tc_rate(clean), mean_of(clean, "p_asr"),
          mean_of(clean, "completion_time_turns"), mean_of(clean, "token_usage"),
          mean_of(clean, "stealth_sim")])))
    for bf in sorted({r.get("branching_factor") for r in rows if r["attacked"] and r.get("branching_factor")}):
        sub = [r for r in rows if r["attacked"] and r.get("branching_factor") == bf]
        print(" | ".join(map(str, [f"Attacked bf={bf}", tc_rate(sub), mean_of(sub, "p_asr"),
              mean_of(sub, "completion_time_turns"), mean_of(sub, "token_usage"),
              mean_of(sub, "stealth_sim")])))
    dec = rows[0]["decode"] if rows else {}
    print(f"\nMethod-A stego decode-success (control): roundtrip_ok={dec.get('roundtrip_ok')} "
          f"capacity={dec.get('capacity_bits')}bits need={dec.get('need_bits')}bits")
    print("results ->", out_path)


if __name__ == "__main__":
    asyncio.run(main())
