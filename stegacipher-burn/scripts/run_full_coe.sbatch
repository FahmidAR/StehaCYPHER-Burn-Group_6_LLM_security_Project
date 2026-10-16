#!/bin/bash
#SBATCH --job-name=stega_full
#SBATCH --partition=coe,defq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=/home/fxr4713/research/StegaCYPHER-Burn/logs/full_%j.log
#SBATCH --error=/home/fxr4713/research/StegaCYPHER-Burn/logs/full_%j.err

echo "Job started: $(date)"; echo "Node: $SLURMD_NODENAME"; nvidia-smi

export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"
ollama serve > /home/fxr4713/research/StegaCYPHER-Burn/logs/full_serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
for i in $(seq 1 30); do curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1 && break; sleep 2; done
ollama pull qwen3.5:35b      # agents
ollama pull qwen3:8b         # fast judge

source /home/fxr4713/miniconda3/etc/profile.d/conda.sh
conda activate corba
cd /home/fxr4713/research/StegaCYPHER-Burn/src

export MODEL_BASE_URL="http://127.0.0.1:11434/v1"
export MODEL_NAME="qwen3.5:35b"      # agents run on 35B
export JUDGE_MODEL="qwen3:8b"        # judging on fast 8B
export MODEL_API_KEY="ollama"
export NUM_TASKS=88                  # all unique benign TAMAS tasks (balanced across 5 domains)
export BF_LIST="3"                   # single bf for the main table (bf-sweep is separate)
export TRIALS=1
export MAX_TURNS=14
export STEGA_OUT=/home/fxr4713/research/StegaCYPHER-Burn/results/full_results.jsonl

python3 run_experiment.py 2>&1 | tee -a /home/fxr4713/research/StegaCYPHER-Burn/results/full_console.log
echo "StegaCIPHER-Burn FULL run segment complete: $(date)"
kill $SERVER_PID 2>/dev/null
