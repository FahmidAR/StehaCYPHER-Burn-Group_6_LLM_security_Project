"""Immutable approval manifest and started-before-request journal."""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import time
from .design import digest


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)


def sign_plan(plan):
    out=copy.deepcopy(plan);out.pop('plan_sha256',None);out['plan_sha256']=digest(out);return out


def require_approval(plan,approved_sha):
    if not approved_sha or approved_sha!=plan.get('plan_sha256') or sign_plan(plan)!=plan:
        raise ValueError('Explicit approval of this exact unchanged plan SHA is required')


def freeze_plan(root,plan):
    require_approval(plan,plan.get('plan_sha256'));root=Path(root);root.mkdir(parents=True,exist_ok=True)
    path=root/'plan.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=plan:raise ValueError('Existing plan differs; never overwrite/mix experiments')
    else:
        with path.open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)


@contextmanager
def exclusive_lock(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if os.name=='nt':
            import msvcrt
            if not stream.seek(0,2):stream.write(b'0');stream.flush()
            stream.seek(0)
            try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:raise ValueError('This experiment already has an active process') from exc
            try:yield
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise ValueError('This experiment already has an active process') from exc
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)


class RunStore:
    def __init__(self,root,plan):
        self.root=Path(root);self.plan=plan;self.cells={c['key']:c for c in plan['cells']}
        freeze_plan(self.root,plan)

    def folder(self,cell):
        if cell.get('key') not in self.cells or cell!=self.cells[cell['key']]:raise ValueError('Cell differs from approved plan')
        return self.root/'attempts'/cell['key']

    def claim(self,cell):
        folder=self.folder(cell);folder.mkdir(parents=True,exist_ok=True)
        try:
            with (folder/'started.json').open('x',encoding='utf-8') as stream:
                json.dump(dict(key=cell['key'],plan_sha256=self.plan['plan_sha256'],started_unix=time.time()),stream)
                stream.flush();os.fsync(stream.fileno())
            return True
        except FileExistsError:return False

    def finish(self,cell,result):
        folder=self.folder(cell)
        if not (folder/'started.json').exists():raise ValueError('Must claim before recording result')
        record=dict(result,key=cell['key'],task_id=cell['task_id'],trial=cell['trial'],
            condition=cell['condition'],position=cell['position'],payload=cell['payload'],human_review='pending')
        if (folder/'result.json').exists():raise ValueError('A terminal attempt cannot be overwritten')
        with (folder/'result.json').open('x',encoding='utf-8') as stream:
            json.dump(record,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())

    def unstarted(self):
        return [c for c in self.plan['cells'] if not (self.folder(c)/'started.json').exists()]

    def records(self):
        records=[]
        for cell in self.plan['cells']:
            folder=self.folder(cell)
            if not (folder/'started.json').exists():continue
            try:record=json.loads((folder/'result.json').read_text(encoding='utf-8'))
            except (FileNotFoundError,json.JSONDecodeError):
                record=dict(key=cell['key'],task_id=cell['task_id'],trial=cell['trial'],
                    condition=cell['condition'],position=cell['position'],payload=cell['payload'],status='interrupted_unknown',human_review='pending')
            records.append(record)
        return records


async def execute_pending(plan,store,run_cell):
    tasks={t['task_id']:t for t in plan['tasks']}
    cells={c['key']:c for c in plan['cells']}
    for key in plan.get('execution_order',list(cells)):
        cell=cells[key]
        if not store.claim(cell):continue
        try:result=await run_cell(tasks[cell['task_id']],cell,plan)
        except Exception as exc:
            result=dict(status='runtime_error',error=f'{type(exc).__name__}: {exc}',
                original_user_task=tasks[cell['task_id']]['benign_query'])
        store.finish(cell,result)
        print(json.dumps(dict(key=cell['key'],status=result['status'])),flush=True)
        if result['status'] in ('runtime_error','scoring_error'):break
    return store.records()
