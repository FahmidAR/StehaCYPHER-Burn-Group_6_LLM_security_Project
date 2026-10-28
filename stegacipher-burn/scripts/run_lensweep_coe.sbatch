#!/bin/bash
#SBATCH --job-name=lensweep
#SBATCH --partition=coe
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=01:30:00
#SBATCH --output=/home/fxr4713/research/StegaCYPHER-Burn/logs/lensweep_%j.log
#SBATCH --error=/home/fxr4713/research/StegaCYPHER-Burn/logs/lensweep_%j.err

echo "Job started: $(date) on $(hostname)"
export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_KEEP_ALIVE=-1
ollama serve > /home/fxr4713/research/StegaCYPHER-Burn/logs/lensweep_serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!
for i in $(seq 1 30); do curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1 && break; sleep 2; done

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
export MODEL_API_KEY="ollama"
export SWEEP_LENGTHS="8,13,20,30,40,50"

python3 decode_length_sweep.py 2>&1 | tee -a /home/fxr4713/research/StegaCYPHER-Burn/results/lensweep_console.log
echo "LENSWEEP COMPLETE: $(date)"
kill $SERVER_PID 2>/dev/null
