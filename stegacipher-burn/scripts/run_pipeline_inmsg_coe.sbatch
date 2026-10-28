#!/bin/bash
#SBATCH --job-name=stega_inmsg
#SBATCH --partition=coe
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/home/fxr4713/research/StegaCYPHER-Burn/logs/inmsg_%j.log
#SBATCH --error=/home/fxr4713/research/StegaCYPHER-Burn/logs/inmsg_%j.err

echo "Job started: $(date) on $(hostname)"
export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_KEEP_ALIVE=-1
ollama serve > /home/fxr4713/research/StegaCYPHER-Burn/logs/inmsg_serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
for i in $(seq 1 30); do curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1 && break; sleep 2; done
ollama list | grep -q "qwen3:8b" || ollama pull qwen3:8b

echo "=== health check ==="
if ! timeout 180 ollama run qwen3.5:35b "Reply with exactly: OK" 2>/dev/null | grep -qi "OK"; then
  echo "HEALTH CHECK FAILED on $(hostname). Aborting."; kill $SERVER_PID 2>/dev/null; exit 1
fi
echo "=== health PASSED ==="

source /home/fxr4713/miniconda3/etc/profile.d/conda.sh
conda activate corba
cd /home/fxr4713/research/StegaCYPHER-Burn/src
export MODEL_BASE_URL="http://127.0.0.1:11434/v1"
export MODEL_NAME="qwen3.5:35b"
export JUDGE_MODEL="qwen3:8b"
export MODEL_API_KEY="ollama"
export STEGO=1
export STEGO_MODE=inmsg        # realistic: benign agents keep normal prompts; hint rides in seed's messages
export NUM_TASKS=10            # 2 per domain, resumable
export BF_LIST="3"
export TRIALS=1
export MAX_TURNS=12
export AGENT_TIMEOUT=300
export AGENT_MAX_RETRIES=1
export JUDGE_TIMEOUT=120
export STEGA_OUT=/home/fxr4713/research/StegaCYPHER-Burn/results/inmsg/inmsg_results.jsonl

python3 run_experiment.py 2>&1 | tee -a /home/fxr4713/research/StegaCYPHER-Burn/results/inmsg_console.log
echo "INMSG RUN COMPLETE: $(date)"
kill $SERVER_PID 2>/dev/null
