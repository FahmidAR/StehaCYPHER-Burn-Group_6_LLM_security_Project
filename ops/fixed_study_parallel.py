"""Operations-only two-replica continuation of an unchanged frozen 880-key study.

No generator/scorer changes, retries, export races, or model calls for calibration.
Run via python -m ops.fixed_study_parallel; all generation stays in frozen modules.
"""
import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from experiments.acrostic_ablation.storage import RunStore, exclusive_lock, save
from ops.fixed_study_resume import management_dir, acknowledged_failures, coverage_audit, require_resume_continuation, seal_resume, continue_on_error, CONTINUABLE_ERRORS

EXPECTED_PLAN='fd5f42a7c7f9e5f870f1fb4f200f8673dd0cdddcff804c7c5fa85153cc6d4fd9'
GPUS=('GPU-9cb844cc-0b77-1281-cd78-dd03339f5cde','GPU-cc7eb4e6-ca0f-bb78-6f10-58dc82acad8a')
CACHE=Path('/home/user4/danhua/class/StegaCIPHER-task-stego-smoke-20261026')
BIN=CACHE/'install/ollama-v0.40.11/bin/ollama'


@contextmanager
def queue_lock(root):
    """Block briefly for the cross-process claim/finish transaction, never inference."""
    path=management_dir(root)/'queue.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if os.name=='nt':
            import msvcrt
            stream.seek(0,2)
            if not stream.tell():stream.write(b'0');stream.flush()
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
            try:yield
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)


def queue_state(root):
    path=management_dir(root)/'queue.json'
    return json.loads(path.read_text()) if path.exists() else {'claims':{}}


def stop_queue(root,reason):
    with queue_lock(root):save(management_dir(root)/'stop.json',dict(reason=reason,time=time.time()))


def process_birth(pid):
    """PID plus OS creation identity, without sending a signal to probe liveness."""
    if os.name=='posix':
        try:return (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
        except (OSError,IndexError):return None
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return None
    try:
        stamps=[wintypes.FILETIME() for _ in range(4)];code=wintypes.DWORD()
        if not kernel.GetProcessTimes(handle,*(ctypes.byref(v) for v in stamps)):return None
        if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value!=259:return None
        return str((stamps[0].dwHighDateTime<<32)|stamps[0].dwLowDateTime)
    finally:kernel.CloseHandle(handle)


def validate_inventory(store):
    for folder in (store.root/'attempts').glob('*'):
        if folder.is_symlink() or folder.name not in store.cells:raise ValueError('Foreign attempt directory: '+folder.name)
        if not (folder/'started.json').exists():raise ValueError('Attempt folder has no start journal: '+folder.name)
        started=json.loads((folder/'started.json').read_text())
        if started.get('key')!=folder.name or started.get('plan_sha256')!=store.plan['plan_sha256']:
            raise ValueError('Attempt journal key/plan mismatch: '+folder.name)


def claim_next(store,worker):
    with queue_lock(store.root):
        if (management_dir(store.root)/'stop.json').exists():return None
        validate_inventory(store)
        state=queue_state(store.root)
        accepted=acknowledged_failures(store)
        keep_running=continue_on_error(store)
        if any(item['worker']==worker and not (store.root/'attempts'/key/'result.json').exists()
            for key,item in state['claims'].items()):raise ValueError('Worker already has an unfinished key')
        for row in store.records():
            if row['status']=='interrupted_unknown':
                owner=state['claims'].get(row['key'])
                if not owner:raise ValueError('Unregistered unfinished key; never retry')
                if not owner.get('birth') or process_birth(owner['pid'])!=owner['birth']:
                    raise ValueError('Unfinished key owner exited or PID was reused; stop claims')
            elif row['status']!='completed' and row['key'] not in accepted and not (keep_running and row['status'] in CONTINUABLE_ERRORS):
                save(management_dir(store.root)/'stop.json',dict(key=row['key'],status=row['status']))
                return None
        for key in store.plan['execution_order']:
            cell=store.cells[key]
            if not store.claim(cell):continue
            state['claims'][key]=dict(worker=worker,pid=os.getpid(),birth=process_birth(os.getpid()),claimed_unix=time.time())
            save(management_dir(store.root)/'queue.json',state)
            return cell
        return None


def finish_claim(store,worker,cell,result):
    with queue_lock(store.root):
        state=queue_state(store.root)
        owner=state['claims'].get(cell['key'],{})
        if (owner.get('worker')!=worker or owner.get('pid')!=os.getpid()
            or owner.get('birth')!=process_birth(os.getpid())):
            raise ValueError('Result does not belong to this worker claim')
        store.finish(cell,result)
        state['claims'][cell['key']].update(finished_unix=time.time(),status=result['status'])
        save(management_dir(store.root)/'queue.json',state)
        if result['status']!='completed' and not (continue_on_error(store) and result['status'] in CONTINUABLE_ERRORS):
            save(management_dir(store.root)/'stop.json',dict(key=cell['key'],status=result['status']))


def require_same_runtime(original,replica):
    url=urlsplit(replica['endpoint'])
    if (url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1')
        or url.path!='/v1' or url.username or url.query or url.fragment):
        raise ValueError('Replica must use an isolated local endpoint')
    if {k:v for k,v in original.items() if k!='endpoint'}!={k:v for k,v in replica.items() if k!='endpoint'}:
        raise ValueError('Replica model/package identity differs from original runtime')


def set_claim_fence(root,enabled):
    """Existing run folder stays writable; next folder creation fails before claim."""
    root=Path(root).resolve();attempts=root/'attempts';record=root/'parallel/drain-permissions.json'
    if os.name!='posix' or os.geteuid()==0:raise ValueError('Requires non-root POSIX ownership')
    if attempts.is_symlink() or attempts.resolve().parent!=root or attempts.stat().st_uid!=os.geteuid():
        raise ValueError('Unsafe attempts directory')
    if enabled:
        if record.exists():raise ValueError('A drain was already requested; do not repeat')
        mode=stat.S_IMODE(attempts.stat().st_mode)
        save(record,dict(original_mode=mode,path=str(attempts),requested_unix=time.time()))
        attempts.chmod(mode & ~0o222)
    else:
        value=json.loads(record.read_text())
        if value['path']!=str(attempts):raise ValueError('Drain path changed')
        attempts.chmod(value['original_mode'])


def read_plan(output):
    from experiments.acrostic_ablation.storage import require_approval
    plan=json.loads((output/'plan.json').read_text())
    require_approval(plan,EXPECTED_PLAN)
    return plan


def snapshot(root):
    paths=[root/'plan.json',root/'runtime.json']+sorted((root/'attempts').glob('*/*'))
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def require_preserved(root,before):
    for relative,wanted in before.items():
        path=root/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:
            raise ValueError('Pre-transition evidence changed: '+relative)


def request_drain(args):
    root=args.output.resolve();read_plan(root)
    proc=Path('/proc')/str(args.legacy_worker_pid)
    argv=(proc/'cmdline').read_bytes().split(b'\0')
    if b'experiments.fixed_carrier_study.cli' not in argv or b'all' not in argv:
        raise ValueError('Legacy worker identity mismatch')
    if (proc/'cwd').resolve()!=Path.cwd().resolve():raise ValueError('Legacy working directory differs')
    store=RunStore(root,read_plan(root));rows=store.records()
    validate_inventory(store)
    if any(r['status'] not in ('completed','interrupted_unknown') for r in rows):raise ValueError('Prior failure blocks transition')
    active=[r['key'] for r in rows if r['status']=='interrupted_unknown']
    if len(active)!=1:raise ValueError('Expected exactly one in-flight legacy key')
    # No pre-existing empty future folders: next mkdir must actually hit the fence.
    for cell in store.unstarted():
        if store.folder(cell).exists():raise ValueError('Unexpected unstarted directory; investigate before fencing')
    completed_prefixes=tuple('attempts/'+r['key']+'/' for r in rows if r['status']=='completed')
    save(root/'parallel/drain-request.json',dict(legacy_pid=args.legacy_worker_pid,
        legacy_birth=process_birth(args.legacy_worker_pid),
        active_key=active[0],completed=sum(r['status']=='completed' for r in rows),
        before_sha256={k:v for k,v in snapshot(root).items() if not k.startswith('attempts/') or k.startswith(completed_prefixes)},
        reason='User authorized two GPUs; finish current native key before replacing serial dispatcher',time=time.time()))
    set_claim_fence(root,True)
    print(json.dumps(dict(drain_requested=True,active_key=active[0]),indent=2))


def seal_transition(args):
    root=args.output.resolve();read_plan(root)
    request=json.loads((root/'parallel/drain-request.json').read_text())
    if process_birth(request['legacy_pid'])==request['legacy_birth']:raise ValueError('Legacy worker still running; keep waiting')
    pipeline=Path.cwd()/'logs/pipeline-result.json'
    if not pipeline.exists():raise ValueError('Legacy controller has not completed owned service cleanup')
    old_log=(Path.cwd()/'logs/formal880.log').read_text()
    if 'PermissionError' not in old_log:raise ValueError('Legacy exit is not the requested claim-boundary fence')
    set_claim_fence(root,False)
    require_preserved(root,request['before_sha256'])
    from experiments.fixed_carrier_study.cli import audit,verify_files,require_continuation
    plan=read_plan(root);verify_files(plan,args.source_repo,args.tamas_dir,root)
    validate_inventory(RunStore(root,plan))
    require_continuation(plan,root,'all')
    save(root/'parallel/transition-audit.json',audit(plan,root,'all',allow_unstarted=True))
    path=root/'parallel/pre-transition-sha256.json'
    if path.exists():raise ValueError('Transition already sealed')
    save(path,snapshot(root))
    print(json.dumps(dict(transition_sealed=True,completed=len(RunStore(root,plan).records())),indent=2))


def validate_completed_result(task,cell,result,journal):
    from experiments.fixed_carrier_study.evidence import check_events
    try:
        events=[json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines() if line]
        issues=check_events(task,cell,result,events)
    except Exception as exc:issues=[f'{type(exc).__name__}: {exc}']
    if issues:result.update(status='evidence_error',evidence_issues=issues)
    return result


def worker(args):
    root=args.output.resolve();plan=read_plan(root)
    from experiments.fixed_carrier_study.cli import verify_files,preflight,configure_environment
    source=verify_files(plan,args.source_repo,args.tamas_dir,root)
    endpoint=f'http://127.0.0.1:{11435+args.worker}/v1'
    transport={**plan,'model_base_url':endpoint}
    fingerprint=preflight(transport)
    require_same_runtime(json.loads((root/'runtime.json').read_text()),fingerprint)
    save(management_dir(root)/f'worker{args.worker}-runtime.json',dict(fingerprint=fingerprint,
        gpu_uuid=GPUS[args.worker],pid=os.getpid(),endpoint_override_only=True))
    configure_environment(transport)
    from autogen_core.models import CreateResult,RequestUsage
    from experiments.acrostic_ablation.runner import load_upstream
    from experiments.fixed_carrier_study.runner import run_cell
    from experiments.fixed_carrier_study.evidence import check_events
    upstream=load_upstream(source,args.tamas_dir)
    upstream['fixed_result']=lambda text:CreateResult(content=text,finish_reason='stop',
        usage=RequestUsage(prompt_tokens=0,completion_tokens=0),cached=False)
    store=RunStore(root,plan);tasks={t['task_id']:t for t in plan['tasks']};name=f'gpu{args.worker}'
    async def run():
        while (cell:=claim_next(store,name)) is not None:
            print(json.dumps(dict(event='CLAIM',worker=name,key=cell['key'],time=time.time())),flush=True)
            sink_errors=[]
            try:
                journal=store.folder(cell)/'events.jsonl'
                with journal.open('x',encoding='utf-8') as stream:
                    def sink(record):
                        try:
                            stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                        except Exception as exc:sink_errors.append(f'{type(exc).__name__}: {exc}');raise
                    result=await run_cell(tasks[cell['task_id']],cell,plan,upstream,sink)
                if result['diagnostics']['transport_errors']:
                    result.update(status='runtime_error',error='Native transport error; original scores retained')
                if sink_errors:result.update(status='evidence_error',evidence_issues=sink_errors)
                if result['status']=='completed':result=validate_completed_result(tasks[cell['task_id']],cell,result,journal)
            except Exception as exc:result=dict(status='evidence_error',error=f'{type(exc).__name__}: {exc}')
            finish_claim(store,name,cell,result)
            print(json.dumps(dict(event='FINISH',worker=name,key=cell['key'],status=result['status'],time=time.time())),flush=True)
    asyncio.run(run())


def gpu_snapshot():
    return subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader'],text=True)


def start_server(root,index):
    port=11435+index;uuid=GPUS[index]
    for line in gpu_snapshot().splitlines():
        fields=[s.strip() for s in line.split(',')]
        if fields[1]==uuid and (int(fields[2].split()[0])>512 or int(fields[3].split()[0])!=0):
            raise ValueError('Requested GPU is no longer idle: '+uuid)
    with socket.socket() as sock:sock.bind(('127.0.0.1',port))
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=uuid,OLLAMA_VULKAN='false',OLLAMA_HOST=f'127.0.0.1:{port}',
        OLLAMA_MODELS=str(CACHE/'models'),OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='2',
        OLLAMA_KEEP_ALIVE='5m',OLLAMA_NO_CLOUD='1',OMP_NUM_THREADS='8',PYTHONUNBUFFERED='1')
    with (management_dir(root)/f'ollama-gpu{index}.log').open('xb') as log:
        process=subprocess.Popen([str(BIN),'serve'],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    register_server(process,BIN,uuid,env['OLLAMA_HOST'])
    try:
        save(management_dir(root)/f'ollama-gpu{index}.json',dict(pid=process.pid,birth=process._scb_birth,gpu_uuid=uuid,port=port,env={k:env[k] for k in (
            'CUDA_VISIBLE_DEVICES','OLLAMA_VULKAN','OLLAMA_HOST','OLLAMA_MODELS','OLLAMA_NUM_PARALLEL',
            'OLLAMA_MAX_LOADED_MODELS','OLLAMA_KEEP_ALIVE','OLLAMA_NO_CLOUD','OMP_NUM_THREADS')}))
    except BaseException:stop_owned_server(process);raise
    return process


def register_server(process,binary,gpu_uuid,host):
    process._scb_binary=Path(binary).resolve();process._scb_birth=process_birth(process.pid)
    process._scb_gpu=gpu_uuid;process._scb_host=host


def owned_members(process):
    """Validate the original session's binaries, creation times, UID and isolation env."""
    leader_birth=process_birth(process.pid)
    if leader_birth is not None and leader_birth!=process._scb_birth:raise ValueError('Server leader PID was reused')
    members=[]
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        pid=int(folder.name)
        try:
            if os.getsid(pid)!=process.pid or os.getpgid(pid)!=process.pid:continue
            fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z':continue
            birth=fields[19];exe=(folder/'exe').resolve()
            env=dict(item.split(b'=',1) for item in (folder/'environ').read_bytes().split(b'\0') if b'=' in item)
            if (folder.stat().st_uid!=os.geteuid() or int(birth)<int(process._scb_birth)
                or not exe.is_relative_to(process._scb_binary.parent.parent)
                or env.get(b'CUDA_VISIBLE_DEVICES')!=process._scb_gpu.encode()
                or env.get(b'OLLAMA_HOST')!=process._scb_host.encode()):
                raise ValueError('Refusing cleanup of an unverified session member')
            if pid==process.pid and exe!=process._scb_binary:raise ValueError('Server executable changed')
            members.append((pid,birth))
        except (FileNotFoundError,ProcessLookupError):continue
    return members


def stop_owned_server(process):
    process.poll()
    for sig,seconds in ((signal.SIGTERM,20),(signal.SIGKILL,5)):
        members=owned_members(process)
        if not members:break
        for pid,birth in members:
            if process_birth(pid)==birth:
                try:os.kill(pid,sig)
                except ProcessLookupError:pass
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            process.poll()
            if not owned_members(process):break
            time.sleep(.1)
    if owned_members(process):raise ValueError('Owned model descendants did not stop')
    process.wait(timeout=5)


@contextmanager
def drain_signals():
    cancelled=[];previous={}
    def handler(signum,frame):cancelled.append(signum)  # no locks/I/O inside signal handler
    for name in ('SIGINT','SIGTERM','SIGHUP'):
        if hasattr(signal,name):
            number=getattr(signal,name);previous[number]=signal.signal(number,handler)
    try:yield cancelled
    finally:
        for number,handler_before in previous.items():signal.signal(number,handler_before)


def wait_for_workers(root,children,servers,cancelled,poll_interval=1):
    while any(child.poll() is None for child in children):
        if cancelled:stop_queue(root,'Controller signal: drain active keys; no further claims')
        if any(child.poll() not in (None,0) for child in children):stop_queue(root,'Worker exited abnormally; no further claims')
        if any(server.poll() is not None for server in servers):stop_queue(root,'Owned server exited; no further claims')
        time.sleep(poll_interval)


def controller(args):
    root=args.output.resolve();plan=read_plan(root);servers=[];children=[];rc=1
    from experiments.fixed_carrier_study.cli import verify_files,require_continuation,audit,preflight
    from experiments.acrostic_ablation.report import write_report
    with exclusive_lock(root/'run.lock'),drain_signals() as cancelled:
        verify_files(plan,args.source_repo,args.tamas_dir,root)
        if os.environ.get('SCB_FIXED_SESSION'):require_resume_continuation(plan,root)
        else:require_continuation(plan,root,'all')
        validate_inventory(RunStore(root,plan))
        before=json.loads((root/'parallel/pre-transition-sha256.json').read_text())
        if os.environ.get('SCB_FIXED_SESSION'):
            authorization=management_dir(root)/'authorization.json'
            os.environ['SCB_FIXED_AUTH_SHA']=hashlib.sha256(authorization.read_bytes()).hexdigest()
            before.update(json.loads(authorization.read_bytes())['before_sha256'])
        require_preserved(root,before)
        start=management_dir(root)/'controller-started.json'
        with start.open('x') as stream:json.dump(dict(pid=os.getpid(),started_unix=time.time(),plan_sha256=EXPECTED_PLAN,
            authorization='User explicitly requested two GPUs; execution infrastructure only',
            operations_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),stream)
        save(management_dir(root)/'controller.pid.json',dict(pid=os.getpid()))
        try:
            for index in range(2):servers.append(start_server(root,index))
            original=json.loads((root/'runtime.json').read_text())
            for index,server in enumerate(servers):
                deadline=time.monotonic()+90;endpoint=f'http://127.0.0.1:{11435+index}/v1'
                while True:
                    if server.poll() is not None:raise ValueError('Owned model server exited before readiness')
                    try:
                        with urlopen(endpoint[:-3]+'/api/version',timeout=2) as response:json.load(response)
                        break
                    except OSError:
                        if time.monotonic()>deadline:raise ValueError('Model metadata readiness timed out')
                        time.sleep(1)
                require_same_runtime(original,preflight({**plan,'model_base_url':endpoint}))
            if cancelled:stop_queue(root,'Signal during startup; do not start new native keys')
            for index in range(2):
                command=[sys.executable,'-m','ops.fixed_study_parallel','--phase','worker','--worker',str(index),
                    '--output',str(root),'--source-repo',str(args.source_repo),'--tamas-dir',str(args.tamas_dir)]
                with (management_dir(root)/f'worker{index}.log').open('xb') as log:
                    children.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
                        env=dict(os.environ,PYTHONUNBUFFERED='1'),start_new_session=True))
            save(management_dir(root)/'worker-pids.json',dict(workers=[p.pid for p in children],servers=[p.pid for p in servers]))
            print('PARALLEL READY: two local replicas; unchanged880 plan',flush=True)
            wait_for_workers(root,children,servers,cancelled)
            require_preserved(root,before)
            store=RunStore(root,plan);validate_inventory(store)
            records=store.records();write_report(root,plan,records)
            checked=audit(plan,root,'all');save(management_dir(root)/'native-audit-all.json',checked)
            save(root/'audit-all.json',checked)
            covered=coverage_audit(store,checked) if os.environ.get('SCB_FIXED_SESSION') else checked
            save(management_dir(root)/'coverage-audit.json',covered)
            verify_files(plan,args.source_repo,args.tamas_dir,root)
            rc=0 if covered['ok'] and not cancelled and all(child.returncode==0 for child in children) else 1
        finally:
            if any(child.poll() is None for child in children):
                stop_queue(root,'Controller cleanup; finish active keys and stop')
                for child in children:child.wait()  # never kill a started native task
            errors=[]
            for server in servers:
                try:stop_owned_server(server)
                except Exception as exc:errors.append(str(exc))
            if errors:rc=1
            save(management_dir(root)/'controller-result.json',dict(exit_code=rc,finished_unix=time.time(),cleanup_errors=errors))
            (management_dir(root)/'final-gpus.csv').write_text(gpu_snapshot())
        print('PARALLEL COVERAGE COMPLETE; see native and coverage audits' if rc==0 else 'PARALLEL STOPPED; retain evidence',flush=True)
        return rc


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['drain','seal','resume-seal','controller','worker'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-repo',type=Path,required=True);parser.add_argument('--tamas-dir',type=Path,required=True)
    parser.add_argument('--legacy-worker-pid',type=int);parser.add_argument('--worker',type=int,choices=[0,1])
    parser.add_argument('--session',default=os.environ.get('SCB_FIXED_SESSION',''))
    args=parser.parse_args(argv)
    os.environ['SCB_FIXED_SESSION']=args.session
    management_dir(args.output)  # reject traversal before any operations
    if args.phase=='drain':request_drain(args)
    elif args.phase=='seal':seal_transition(args)
    elif args.phase=='resume-seal':seal_resume(args)
    elif args.phase=='worker':worker(args)
    else:return controller(args)
    return 0


if __name__=='__main__':sys.exit(main())
