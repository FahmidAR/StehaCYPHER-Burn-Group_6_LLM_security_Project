#!/usr/bin/env bash
# One detached transition; Linux tests must pass BEFORE any claim fence is set.
set -euo pipefail
ROOT=/home/user4/danhua/class/StegaCIPHER-fixed-study-20261026
PYTHON=/home/user4/danhua/class/StehaCYPHER-Burn-week7/.venv/bin/python
REPO=/home/user4/danhua/class/StehaCYPHER-Burn-final-20261020
TAMAS=/home/user4/danhua/class/StehaCYPHER-Burn-week7/.external/TAMAS
OUT=results/fixed-carrier-study-v1
cd "$ROOT"
exec >>logs/two-gpu-transition.log 2>&1
exec 9>logs/two-gpu-transition.lock
flock -n 9 || { echo TRANSITION_ALREADY_RUNNING; exit 9; }
echo "TWO_GPU_TRANSITION $(date -u +%FT%TZ) pid=$$"
echo $$ >logs/two-gpu-transition.pid
"$PYTHON" -m unittest discover -s ops/tests -p test_fixed_study_parallel.py -v >logs/two-gpu-linux-tests.log 2>&1
[[ ! -e "$OUT/parallel/controller-started.json" ]] || { echo DO_NOT_RELAUNCH_CONTROLLER; exit 9; }
ARGS=(--output "$OUT" --source-repo "$REPO" --tamas-dir "$TAMAS")
if [[ ! -e "$OUT/parallel/drain-request.json" ]]; then
  # No queue mutation if the second card is now busy or the legacy identity is lost.
  LEGACY_PID=$("$PYTHON" - <<'PY'
import json,os
from pathlib import Path
from ops.fixed_study_parallel import GPUS,gpu_snapshot
fields=next(line.split(',') for line in gpu_snapshot().splitlines() if GPUS[1] in line)
assert int(fields[2].split()[0])<512 and int(fields[3].split()[0])==0,'GPU1 is occupied; leave serial job running'
found=[]
for folder in Path('/proc').iterdir():
    if not folder.name.isdigit():continue
    try:
        argv=(folder/'cmdline').read_bytes().split(b'\0')
        if b'experiments.fixed_carrier_study.cli' in argv and b'all' in argv and (folder/'cwd').resolve()==Path.cwd():found.append(int(folder.name))
    except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert len(found)==1,'Expected exactly one owned serial worker'
print(found[0])
PY
)
  "$PYTHON" -m ops.fixed_study_parallel --phase drain --legacy-worker-pid "$LEGACY_PID" "${ARGS[@]}"
fi
echo "WAITING FOR CURRENT NATIVE KEY; no request interruption $(date -u +%FT%TZ)"
"$PYTHON" - <<'PY'
import json,time
from pathlib import Path
from ops.fixed_study_parallel import process_birth
request=json.loads(Path('results/fixed-carrier-study-v1/parallel/drain-request.json').read_text())
while process_birth(request['legacy_pid'])==request['legacy_birth']:time.sleep(1)
while not Path('logs/pipeline-result.json').exists():time.sleep(1)
PY
if [[ ! -e "$OUT/parallel/pre-transition-sha256.json" ]]; then
  "$PYTHON" -m ops.fixed_study_parallel --phase seal "${ARGS[@]}"
fi
echo "LEGACY DRAIN SEALED; START TWO REPLICAS $(date -u +%FT%TZ)"
exec "$PYTHON" -m ops.fixed_study_parallel --phase controller "${ARGS[@]}"
