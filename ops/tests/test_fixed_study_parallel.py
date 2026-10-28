"""Concurrency tests use real RunStore files and independent OS processes."""
import asyncio
import copy
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import signal
import subprocess
import sys
import time
import unittest

from experiments.acrostic_ablation.storage import RunStore, execute_pending, sign_plan


def fixture_plan():
    return sign_plan(dict(cells=[dict(key=str(i), task_id='task', trial=1,
        condition='clean', position=None, payload=None) for i in range(12)],
        tasks=[dict(task_id='task', benign_query='Original request')],
        execution_order=[str(i) for i in range(12)]))


def consume(root, plan, worker, barrier):
    module=importlib.import_module('ops.fixed_study_parallel')
    store=RunStore(root, plan)
    first=True
    while (cell:=module.claim_next(store, worker)) is not None:
        if first:barrier.wait(15);first=False
        module.finish_claim(store, worker, cell, dict(status='completed', worker=worker))


class ParallelTests(unittest.TestCase):
    def module(self):
        try: return importlib.import_module('ops.fixed_study_parallel')
        except ModuleNotFoundError: self.fail('Missing safe two-worker operations scheduler')

    def test_concurrent_claims_complete_every_key_exactly_once_and_preserve_prior_result(self):
        module=self.module(); plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td:
            store=RunStore(td, plan); first=plan['cells'][0]
            store.claim(first); store.finish(first, dict(status='completed', worker='legacy'))
            before=(store.folder(first)/'result.json').read_bytes()
            context=multiprocessing.get_context('spawn')
            barrier=context.Barrier(2)
            children=[context.Process(target=consume, args=(td,plan,w,barrier)) for w in ('gpu0','gpu1')]
            for child in children: child.start()
            for child in children: child.join(20); self.assertEqual(child.exitcode,0)
            rows=store.records()
            self.assertEqual(len(rows),12); self.assertEqual({r['status'] for r in rows},{'completed'})
            self.assertEqual((store.folder(first)/'result.json').read_bytes(),before)
            allocation=json.loads((Path(td)/'parallel/queue.json').read_text())['claims']
            self.assertEqual(set(allocation), {str(i) for i in range(1,12)})
            self.assertEqual({v['worker'] for v in allocation.values()},{'gpu0','gpu1'})

    def test_failure_stops_new_claims_but_preserves_other_inflight_result(self):
        module=self.module(); plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td:
            store=RunStore(td,plan)
            a=module.claim_next(store,'gpu0'); b=module.claim_next(store,'gpu1')
            module.finish_claim(store,'gpu0',a,dict(status='runtime_error',error='real failure'))
            module.finish_claim(store,'gpu1',b,dict(status='completed'))
            self.assertIsNone(module.claim_next(store,'gpu1'))
            self.assertEqual([r['status'] for r in store.records()],['runtime_error','completed'])
            self.assertEqual(len(list(Path(td).glob('attempts/*/started.json'))),2)

    def test_unregistered_started_key_blocks_new_claim_instead_of_retrying(self):
        module=self.module(); plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td:
            store=RunStore(td,plan);store.claim(plan['cells'][0])
            with self.assertRaisesRegex(ValueError,'unregistered|unfinished'):
                module.claim_next(store,'gpu0')
            self.assertEqual(len(list(Path(td).glob('attempts/*/started.json'))),1)

    def test_dead_registered_worker_and_foreign_journals_block_claims(self):
        module=self.module();plan=fixture_plan()
        for variant in ('dead_worker','foreign_key','wrong_sha'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as td:
                root=Path(td);store=RunStore(root,plan)
                if variant=='dead_worker':
                    module.claim_next(store,'gpu0')
                    path=root/'parallel/queue.json';state=json.loads(path.read_text())
                    state['claims']['0']['pid']=2147483647
                    path.write_text(json.dumps(state))
                else:
                    folder=root/'attempts'/('foreign' if variant=='foreign_key' else '0');folder.mkdir(parents=True)
                    (folder/'started.json').write_text(json.dumps({'key':folder.name,'plan_sha256':'wrong'}))
                with self.assertRaises(ValueError):module.claim_next(store,'gpu1')
                self.assertFalse((root/'attempts/1/started.json').exists())

    def test_wrong_process_cannot_finish_another_process_claim(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);store=RunStore(root,plan);cell=module.claim_next(store,'gpu0')
            path=root/'parallel/queue.json';state=json.loads(path.read_text())
            state['claims']['0']['pid']=2147483647;path.write_text(json.dumps(state))
            with self.assertRaises(ValueError):module.finish_claim(store,'gpu0',cell,dict(status='completed'))
            self.assertFalse((store.folder(cell)/'result.json').exists())

    @unittest.skipUnless(os.name=='posix','POSIX signals on deployment host')
    def test_termination_drains_worker_and_executes_cleanup(self):
        self.module()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            code='from ops.tests.test_fixed_study_parallel import signal_driver; signal_driver('+repr(td)+')'
            driver=subprocess.Popen([sys.executable,'-c',code],start_new_session=True)
            try:
                deadline=time.monotonic()+10
                while not (root/'ready').exists() and driver.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue((root/'ready').exists())
                os.killpg(driver.pid,signal.SIGTERM)
                self.assertEqual(driver.wait(timeout=10),0)
                rows=RunStore(root,fixture_plan()).records()
                self.assertEqual([(r['key'],r['status']) for r in rows],[('0','completed')])
                self.assertTrue((root/'cleanup').exists())
            finally:
                if driver.poll() is None:driver.kill();driver.wait()

    @unittest.skipUnless(os.name=='posix','Linux owned-session cleanup')
    def test_cleanup_reaps_verified_runner_after_server_leader_exited(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);host='fixture-localhost:11435';gpu='fixture-only'
            child_code='import time; time.sleep(60)'
            code=('import subprocess,sys,time; from pathlib import Path; '
                'p=subprocess.Popen([sys.executable,"-c",'+repr(child_code)+']); '
                'Path('+repr(str(root/'child.pid'))+').write_text(str(p.pid)); '
                'time.sleep(.3)')
            process=subprocess.Popen([sys.executable,'-c',code],start_new_session=True,
                env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu,OLLAMA_HOST=host))
            module.register_server(process,Path(sys.executable),gpu,host)
            try:
                process.wait(timeout=10)
                self.assertTrue(module.owned_members(process),'Fixture runner did not survive leader')
                module.stop_owned_server(process)
                self.assertEqual(module.owned_members(process),[])
            finally:
                if process.poll() is None:process.kill();process.wait()
                path=root/'child.pid'
                if path.exists():
                    try:os.kill(int(path.read_text()),signal.SIGKILL)
                    except ProcessLookupError:pass

    def test_endpoint_normalization_cannot_hide_model_or_package_changes(self):
        module=self.module()
        original=dict(endpoint='http://127.0.0.1:11435/v1',packages={'openai':'3.26.0'},
            ollama_models={'qwen3.5:35b':{'digest':'frozen-weights'}})
        replica=copy.deepcopy(original); replica['endpoint']='http://127.0.0.1:11436/v1'
        module.require_same_runtime(original,replica)
        for changed in ({**replica,'packages':{'openai':'different'}},
            {**replica,'ollama_models':{'qwen3.5:35b':{'digest':'different'}}},
            {**replica,'endpoint':'https://outside.example/v1'}):
            with self.assertRaises(ValueError): module.require_same_runtime(original,changed)

    @unittest.skipUnless(os.name=='posix' and getattr(os,'geteuid',lambda:0)()!=0,
        'POSIX non-root permission boundary required; run on server too')
    def test_boundary_fence_finishes_inflight_and_never_starts_next_key(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); store=RunStore(root,plan); calls=[]
            async def run(task,cell,p):
                calls.append(cell['key']); module.set_claim_fence(root, True)
                (store.folder(cell)/'events.jsonl').write_text('current run can finish')
                return dict(status='completed')
            try:
                with self.assertRaises(PermissionError):asyncio.run(execute_pending(plan,store,run))
                self.assertEqual(calls,['0'])
                self.assertEqual([(r['key'],r['status']) for r in store.records()],[('0','completed')])
            finally:module.set_claim_fence(root,False)
            self.assertTrue(store.claim(plan['cells'][1]))


def delayed_consumer(root):
    module=importlib.import_module('ops.fixed_study_parallel');store=RunStore(root,fixture_plan())
    cell=module.claim_next(store,'gpu0');(Path(root)/'ready').touch();time.sleep(.5)
    module.finish_claim(store,'gpu0',cell,dict(status='completed'))
    if module.claim_next(store,'gpu0') is not None:raise RuntimeError('Claimed after termination request')


def signal_driver(root):
    module=importlib.import_module('ops.fixed_study_parallel')
    RunStore(root,fixture_plan())
    with module.drain_signals() as cancelled:
        code='from ops.tests.test_fixed_study_parallel import delayed_consumer; delayed_consumer('+repr(root)+')'
        child=subprocess.Popen([sys.executable,'-c',code],start_new_session=True)
        try:module.wait_for_workers(Path(root),[child],[],cancelled,poll_interval=.01)
        finally:(Path(root)/'cleanup').touch()
        if child.returncode!=0:raise RuntimeError('Worker was interrupted')


if __name__=='__main__':unittest.main()
