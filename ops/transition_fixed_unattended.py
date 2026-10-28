"""Drain the verified current controller, then continue terminal errors unattended."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from experiments.acrostic_ablation.storage import exclusive_lock,save,RunStore
from ops.fixed_study_parallel import process_birth,queue_lock,read_plan,snapshot,require_preserved


def main():
    root=Path('results/fixed-carrier-study-v1').resolve();read_plan(root)
    new=root/'parallel/sessions/resume-20261027-unattended'
    if new.exists():raise ValueError('Unattended session already exists; do not relaunch')
    old=root/'parallel/sessions/resume-20261027-c'
    controller=json.loads((old/'controller.pid.json').read_text());pid=controller['pid']
    expected_birth='233308625'
    os.environ['SCB_FIXED_SESSION']='resume-20261027-c'
    with exclusive_lock(Path('logs/unattended-transition.lock')):
        with (old/'unattended-drain-request.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(user_instruction='失败了也继续跑；不用监控',pid=pid,birth=expected_birth,requested_unix=time.time()),stream)
        terminal_keys={r['key'] for r in RunStore(root,read_plan(root)).records() if r['status']!='interrupted_unknown'}
        before={k:v for k,v in snapshot(root).items() if not k.startswith('attempts/') or k.split('/')[1] in terminal_keys}
        if process_birth(pid) is not None:
            proc=Path('/proc')/str(pid);argv=(proc/'cmdline').read_bytes().split(b'\0')
            if (pid!=2483770 or process_birth(pid)!=expected_birth or (proc/'cwd').resolve()!=Path.cwd().resolve()
                or (proc/'exe').resolve()!=Path(sys.executable).resolve() or b'ops.fixed_study_parallel' not in argv
                or b'controller' not in argv or b'resume-20261027-c' not in argv):
                raise ValueError('Refusing to signal an unverified controller')
            with queue_lock(root):
                if not (old/'stop.json').exists():save(old/'stop.json',dict(reason='User-authorized drain to continue-on-error policy',time=time.time()))
            if process_birth(pid)==expected_birth:
                try:os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
            while process_birth(pid)==expected_birth:time.sleep(1)
        if not (old/'controller-result.json').exists():raise ValueError('Previous controller cleanup result missing')
        require_preserved(root,before)
        args=['--output',str(root),'--source-repo','/home/user4/danhua/class/StehaCYPHER-Burn-final-20261020',
            '--tamas-dir','/home/user4/danhua/class/StehaCYPHER-Burn-week7/.external/TAMAS','--session','resume-20261027-unattended']
        subprocess.check_call([sys.executable,'-m','ops.fixed_study_parallel','--phase','resume-seal']+args)
        print('DRAIN COMPLETE; START UNATTENDED CONTINUE-ON-ERROR',flush=True)
    os.execv(sys.executable,[sys.executable,'-m','ops.fixed_study_parallel','--phase','controller']+args)


if __name__=='__main__':main()
