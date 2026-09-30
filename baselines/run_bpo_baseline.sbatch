#!/bin/bash
#SBATCH --job-name=bpo-baseline
#SBATCH --partition=coe
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=/home/fxr4713/PromSkillGuardian/logs/bpo_baseline/slurm_%j.log
#SBATCH --error=/home/fxr4713/PromSkillGuardian/logs/bpo_baseline/slurm_%j.err

echo "Job started: $(date)"
echo "Node: $SLURMD_NODENAME"
echo "GPU: $CUDA_VISIBLE_DEVICES"
nvidia-smi

python3 /home/fxr4713/PromSkillGuardian/baselines/bpo_baseline.py \
  --dataset D1 \
  --iterations 1 \
  --max-new-tokens 512 \
  --out-dir /home/fxr4713/PromSkillGuardian/baselines/out/bpo

echo "Job finished: $(date)"
