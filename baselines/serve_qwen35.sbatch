#!/bin/bash
#SBATCH --job-name=ollama-qwen35-promsec
#SBATCH --partition=coe
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/home/fxr4713/PromSkillGuardian/logs/ollama-qwen35/slurm_%j.log
#SBATCH --error=/home/fxr4713/PromSkillGuardian/logs/ollama-qwen35/slurm_%j.err

echo "Job started: $(date)"
echo "Node: $SLURMD_NODENAME"
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi

export OLLAMA_HOST=0.0.0.0:11434
export PATH="$HOME/.local/bin:$PATH"

echo "Starting ollama serve..."
ollama serve > /home/fxr4713/PromSkillGuardian/logs/ollama-qwen35/serve_${SLURM_JOB_ID}.log 2>&1 &
SERVER_PID=$!

# wait for server to come up
for i in $(seq 1 30); do
  if curl -s "http://127.0.0.1:11434/api/version" >/dev/null 2>&1; then
    echo "Ollama server is up."
    break
  fi
  sleep 2
done

echo "Pulling qwen3.5:35b (this can take a while, ~24GB)..."
ollama pull qwen3.5:35b

# publish endpoint for other jobs to consume
echo "${SLURMD_NODENAME}:11434" > /home/fxr4713/PromSkillGuardian/baselines/ollama_endpoint.txt
echo "Endpoint published: $(cat /home/fxr4713/PromSkillGuardian/baselines/ollama_endpoint.txt)"

echo "Server ready. Holding job open for experiments until time limit..."
wait $SERVER_PID
