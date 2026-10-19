#!/bin/bash
#SBATCH --job-name=stega_pipeline
#SBATCH --partition=coe
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=14:00:00
#SBATCH --output=/home/fxr4713/research/StegaCYPHER-Burn/logs/pipeline_%j.log
#SBATCH --error=/home/fxr4713/research/StegaCYPHER-Burn/logs/pipeline_%j.err

echo "Job started: $(date) on $(hostname)"; nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv
export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_KEEP_ALIVE=-1        # keep the model resident (no cold reload per call)
ollama serve > /home/fxr4713/research/StegaCYPHER-Burn/logs/pipeline_serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
for i in $(seq 1 30); do curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1 && break; sleep 2; done

# models are already on disk (qwen3.5:35b, qwen3:8b); only pull the judge if missing.
ollama list | grep -q "qwen3:8b" || ollama pull qwen3:8b

# --- FAST-FAIL HEALTH CHECK: confirm the 35b actually generates on THIS node's GPU.
# If it can't produce a token in 180s, the node is bad -> exit now instead of
# wasting the whole wall-clock (the 16h no-progress failure on h100-8s-04).
echo "=== health check: warming qwen3.5:35b ==="
if ! timeout 180 ollama run qwen3.5:35b "Reply with exactly: OK" 2>/dev/null | grep -qi "OK"; then
  echo "HEALTH CHECK FAILED: qwen3.5:35b did not generate within 180s on $(hostname). Aborting so we can resubmit onto a good node."
  nvidia-smi
  kill $SERVER_PID 2>/dev/null
  exit 1
fi
echo "=== health check PASSED: model generates on GPU ==="

source /home/fxr4713/miniconda3/etc/profile.d/conda.sh
conda activate corba
cd /home/fxr4713/research/StegaCYPHER-Burn/src

export MODEL_BASE_URL="http://127.0.0.1:11434/v1"
export MODEL_NAME="qwen3.5:35b"
export JUDGE_MODEL="qwen3:8b"
export MODEL_API_KEY="ollama"
export STEGO=1                 # covert acrostic delivery of the attack trigger
export NUM_TASKS=88            # full dedup'd benign TAMAS set (resumable; 8-task slice already validated)
export BF_LIST="3"
export TRIALS=1
export MAX_TURNS=12
export AGENT_TIMEOUT=300       # fail a stuck call in 5 min, not 15
export AGENT_MAX_RETRIES=1
export JUDGE_TIMEOUT=120
export STEGA_OUT=/home/fxr4713/research/StegaCYPHER-Burn/results/pipeline_results.jsonl

python3 run_experiment.py 2>&1 | tee -a /home/fxr4713/research/StegaCYPHER-Burn/results/pipeline_console.log
echo "PIPELINE RUN COMPLETE: $(date)"
kill $SERVER_PID 2>/dev/null
