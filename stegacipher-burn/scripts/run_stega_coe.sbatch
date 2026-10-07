#!/bin/bash
#SBATCH --job-name=stega_v1
#SBATCH --partition=coe,defq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/home/fxr4713/research/StegaCYPHER-Burn/logs/slurm_%j.log
#SBATCH --error=/home/fxr4713/research/StegaCYPHER-Burn/logs/slurm_%j.err

echo "Job started: $(date)"; echo "Node: $SLURMD_NODENAME"; echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi

export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"
ollama serve > /home/fxr4713/research/StegaCYPHER-Burn/logs/serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
for i in $(seq 1 30); do curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1 && break; sleep 2; done
ollama pull qwen3.5:35b

source /home/fxr4713/miniconda3/etc/profile.d/conda.sh
conda activate corba
cd /home/fxr4713/research/StegaCYPHER-Burn/src

export MODEL_BASE_URL="http://127.0.0.1:11434/v1"
export MODEL_NAME="qwen3.5:35b"
export MODEL_API_KEY="ollama"
export NUM_TASKS=2
export BRANCHING_FACTOR=3
export MAX_TURNS=12
export STEGA_OUT=/home/fxr4713/research/StegaCYPHER-Burn/results/v1_results.jsonl

python3 run_experiment.py 2>&1 | tee /home/fxr4713/research/StegaCYPHER-Burn/results/v1_console.log

echo "StegaCIPHER-Burn v1 complete: $(date)"
kill $SERVER_PID 2>/dev/null
