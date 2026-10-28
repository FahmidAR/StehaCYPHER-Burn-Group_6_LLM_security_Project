import asyncio
from pathlib import Path
import tempfile
import unittest
from experiments.acrostic_ablation.design import build_plan
try:
    from experiments.acrostic_ablation import storage as s
except ImportError:
    s=None

TASK=dict(task_id='t',benign_query='Draft a memo.',agents=[dict(name='A',desc='Draft')])


class StorageTests(unittest.TestCase):
    def module(self):self.assertIsNotNone(s,'approval/journal implementation missing');return s

    def test_changed_plan_or_wrong_approval_never_passes(self):
        m=self.module();plan=m.sign_plan(build_plan([TASK]))
        m.require_approval(plan,plan['plan_sha256'])
        with self.assertRaises(ValueError):m.require_approval(plan,'wrong')
        plan['profile']['max_turns']=99
        with self.assertRaises(ValueError):m.require_approval(plan,plan['plan_sha256'])

    def test_manifest_cannot_be_replaced_by_different_experiment(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            first=m.sign_plan(build_plan([TASK]));m.freeze_plan(Path(tmp),first);m.freeze_plan(Path(tmp),first)
            second=m.sign_plan(build_plan([TASK],payloads=['GO']))
            with self.assertRaises(ValueError):m.freeze_plan(Path(tmp),second)

    def test_started_and_failed_runs_are_retained_not_retried(self):
        m=self.module();plan=m.sign_plan(build_plan([TASK]))
        with tempfile.TemporaryDirectory() as tmp:
            store=m.RunStore(Path(tmp),plan);cell=plan['cells'][0]
            self.assertTrue(store.claim(cell));self.assertFalse(store.claim(cell))
            store.finish(cell,{'status':'runtime_error','error':'service failed'})
            self.assertFalse(store.claim(cell));self.assertEqual(store.records()[0]['status'],'runtime_error')
            with self.assertRaises(ValueError):store.finish(cell,{'status':'completed'})

    def test_failure_stops_batch_and_no_second_model_call_is_made(self):
        m=self.module();plan=m.sign_plan(build_plan([TASK]));calls=[]
        async def failing(task,cell,plan):calls.append(cell['key']);raise RuntimeError('model down')
        with tempfile.TemporaryDirectory() as tmp:
            store=m.RunStore(Path(tmp),plan)
            asyncio.run(m.execute_pending(plan,store,failing))
            self.assertEqual(len(calls),1);self.assertEqual(len(store.records()),1)
            self.assertEqual(store.records()[0]['status'],'runtime_error')
            self.assertEqual(len(store.unstarted()),6)

    def test_interrupted_started_cell_is_unknown_and_never_automatically_restarted(self):
        m=self.module();plan=m.sign_plan(build_plan([TASK]))
        with tempfile.TemporaryDirectory() as tmp:
            store=m.RunStore(Path(tmp),plan);store.claim(plan['cells'][0])
            record=store.records()[0]
            self.assertEqual(record['status'],'interrupted_unknown')
            self.assertFalse(store.claim(plan['cells'][0]))


if __name__=='__main__':unittest.main()
