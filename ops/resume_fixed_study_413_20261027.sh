#!/usr/bin/env bash
# User-authorized remaining-only continuation; never repeat this launch.
set -euo pipefail
ROOT=/home/user4/danhua/class/StegaCIPHER-fixed-study-20261026
PYTHON=/home/user4/danhua/class/StehaCYPHER-Burn-week7/.venv/bin/python
cd "$ROOT"
exec >>logs/resume-20261027-b.log 2>&1
exec 9>logs/resume-20261027-b.lock
flock -n 9 || exit 9
ARGS=(--output results/fixed-carrier-study-v1
  --source-repo /home/user4/danhua/class/StehaCYPHER-Burn-final-20261020
  --tamas-dir /home/user4/danhua/class/StehaCYPHER-Burn-week7/.external/TAMAS
  --session resume-20261027-b)
[[ ! -e results/fixed-carrier-study-v1/parallel/sessions/resume-20261027-b ]] || { echo SESSION_ALREADY_EXISTS_DO_NOT_RELAUNCH; exit 9; }
"$PYTHON" -m unittest ops.tests.test_fixed_study_parallel ops.tests.test_fixed_study_resume -v
"$PYTHON" -m ops.fixed_study_parallel --phase resume-seal "${ARGS[@]}"
exec "$PYTHON" -m ops.fixed_study_parallel --phase controller "${ARGS[@]}"
