"""Operations amendments never retry or relabel the acknowledged runtime failure."""
import hashlib
import importlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.acrostic_ablation.storage import RunStore, save
from ops.tests.test_fixed_study_parallel import fixture_plan, consume


def consume_with_errors(root,plan,worker,barrier):
    scheduler=importlib.import_module('ops.fixed_study_parallel');store=RunStore(root,plan);first=True
    while (cell:=scheduler.claim_next(store,worker)) is not None:
        if first:barrier.wait(15);first=False
        status='runtime_error' if int(cell['key'])%3==0 else 'scoring_error' if int(cell['key'])%4==0 else 'completed'
        scheduler.finish_claim(store,worker,cell,dict(status=status))


class ResumeTests(unittest.TestCase):
    def module(self):
        try:return importlib.import_module('ops.fixed_study_resume')
        except ModuleNotFoundError:self.fail('Missing explicit acknowledged-failure session support')

    def setup_session(self, root, plan, failed_count=1):
        module=self.module();store=RunStore(root,plan)
        for cell in plan['cells'][:failed_count]:
            store.claim(cell);store.finish(cell,dict(status='runtime_error',error='Preserved native failure'))
        old=Path(root)/'parallel';save(old/'stop.json',{'key':'0'})
        save(old/'controller-result.json',{'exit_code':1,'cleanup_errors':[]})
        session=module.management_dir(root);session.mkdir(parents=True)
        failures={str(i):hashlib.sha256((Path(root)/'attempts'/str(i)/'result.json').read_bytes()).hexdigest()
            for i in range(failed_count)}
        save(session/'authorization.json',dict(plan_sha256=plan['plan_sha256'],acknowledged_failures=failures))
        return store

    def test_explicit_unattended_policy_finishes_all_keys_despite_runtime_and_scoring_errors(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-20261027-unattended'):
            store=self.setup_session(td,plan)
            auth=module.management_dir(td)/'authorization.json';value=json.loads(auth.read_text())
            value['continue_on_error']=True;save(auth,value)
            before=(Path(td)/'attempts/0/result.json').read_bytes()
            context=multiprocessing.get_context('spawn');barrier=context.Barrier(2)
            children=[context.Process(target=consume_with_errors,args=(td,plan,w,barrier)) for w in ('gpu0','gpu1')]
            for child in children:child.start()
            for child in children:child.join(25)
            for child in children:self.assertEqual(child.exitcode,0)
            rows=store.records();self.assertEqual(len(rows),12)
            self.assertEqual((Path(td)/'attempts/0/result.json').read_bytes(),before)
            self.assertFalse((module.management_dir(td)/'stop.json').exists())
            self.assertTrue(any(r['status']=='runtime_error' and r['key']!='0' for r in rows))
            self.assertTrue(any(r['status']=='scoring_error' for r in rows))
            native={'ok':False,'issues':[r['key']+': '+r['status'] for r in rows if r['status']!='completed']}
            self.assertTrue(module.coverage_audit(store,native)['ok']);self.assertFalse(native['ok'])
            native['issues'].append('CSV score mismatch')
            self.assertFalse(module.coverage_audit(store,native)['ok'])

    def test_unattended_policy_still_blocks_evidence_errors_and_unknown_started_keys(self):
        module=self.module();scheduler=importlib.import_module('ops.fixed_study_parallel');plan=fixture_plan()
        for variant in ('evidence','unknown'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-20261027-unattended'):
                store=self.setup_session(td,plan)
                auth=module.management_dir(td)/'authorization.json';value=json.loads(auth.read_text());value['continue_on_error']=True;save(auth,value)
                if variant=='evidence':
                    cell=scheduler.claim_next(store,'gpu0');scheduler.finish_claim(store,'gpu0',cell,dict(status='evidence_error'))
                    self.assertIsNone(scheduler.claim_next(store,'gpu1'))
                else:
                    store.claim(plan['cells'][1])
                    with self.assertRaises(ValueError):scheduler.claim_next(store,'gpu1')

    def test_journal_and_validator_exceptions_remain_evidence_errors_under_continue_policy(self):
        scheduler=importlib.import_module('ops.fixed_study_parallel')
        self.assertTrue(hasattr(scheduler,'validate_completed_result'),'Missing evidence exception classification')
        for invalid_json in (True,False):
            with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-20261027-unattended'):
                store=self.setup_session(td,fixture_plan());module=self.module()
                auth=module.management_dir(td)/'authorization.json';value=json.loads(auth.read_text());value['continue_on_error']=True;save(auth,value)
                cell=scheduler.claim_next(store,'gpu0');journal=store.folder(cell)/'events.jsonl'
                journal.write_text('not json' if invalid_json else '{"kind":"sample"}\n',encoding='utf-8')
                with patch('experiments.fixed_carrier_study.evidence.check_events',side_effect=ValueError('validator failed')):
                    result=scheduler.validate_completed_result({},cell,dict(status='completed'),journal)
                self.assertEqual(result['status'],'evidence_error')
                scheduler.finish_claim(store,'gpu0',cell,result)
                self.assertIsNone(scheduler.claim_next(store,'gpu1'))

    def test_two_preserved_failures_concurrent_remaining_only_and_third_failure_stops(self):
        module=self.module();scheduler=importlib.import_module('ops.fixed_study_parallel');plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=2)
            before={p:p.read_bytes() for p in Path(td).glob('attempts/*/*')}
            context=multiprocessing.get_context('spawn');barrier=context.Barrier(2)
            children=[context.Process(target=consume,args=(td,plan,w,barrier)) for w in ('gpu0','gpu1')]
            for child in children:child.start()
            for child in children:child.join(25)
            for child in children:self.assertEqual(child.exitcode,0)
            self.assertEqual(sum(r['status']=='completed' for r in store.records()),10)
            self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))
            state=json.loads((module.management_dir(td)/'queue.json').read_text())
            self.assertEqual(set(state['claims']),set(map(str,range(2,12))))
            native={'ok':False,'issues':['0: runtime_error','1: runtime_error']}
            self.assertTrue(module.coverage_audit(store,native)['ok'])
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=2)
            cell=scheduler.claim_next(store,'gpu0')
            scheduler.finish_claim(store,'gpu0',cell,dict(status='runtime_error',error='third failure'))
            self.assertIsNone(scheduler.claim_next(store,'gpu1'))
            self.assertEqual(len(store.records()),3)

    def test_authorization_inventory_rejects_unknown_or_extra_failure_or_wrong_pending_count(self):
        module=self.module();plan=fixture_plan()
        self.assertTrue(hasattr(module,'validate_resume_inventory'),'Missing exact continuation scope validation')
        profile=dict(started=2,pending=10,keys={'0','1'})
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=2)
            module.validate_resume_inventory(store,profile)
            with self.assertRaises(ValueError):module.validate_resume_inventory(store,{**profile,'pending':9})
            store.claim(plan['cells'][2])
            with self.assertRaises(ValueError):module.validate_resume_inventory(store,{**profile,'started':3,'pending':9})
            store.finish(plan['cells'][2],dict(status='runtime_error',error='unapproved'))
            with self.assertRaises(ValueError):module.validate_resume_inventory(store,{**profile,'started':3,'pending':9})

    def test_three_preserved_failures_keep_bytes_and_only_run_remaining_then_stop_on_new_error(self):
        module=self.module();scheduler=importlib.import_module('ops.fixed_study_parallel');plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=3)
            before={p:p.read_bytes() for p in Path(td).glob('attempts/*/*')}
            context=multiprocessing.get_context('spawn');barrier=context.Barrier(2)
            children=[context.Process(target=consume,args=(td,plan,w,barrier)) for w in ('gpu0','gpu1')]
            for child in children:child.start()
            for child in children:child.join(25)
            for child in children:self.assertEqual(child.exitcode,0)
            self.assertEqual(sum(r['status']=='completed' for r in store.records()),9)
            self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))
            state=json.loads((module.management_dir(td)/'queue.json').read_text())
            self.assertEqual(set(state['claims']),set(map(str,range(3,12))))
            native={'ok':False,'issues':[str(i)+': runtime_error' for i in range(3)]}
            self.assertTrue(module.coverage_audit(store,native)['ok']);self.assertFalse(native['ok'])
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=3)
            cell=scheduler.claim_next(store,'gpu0')
            scheduler.finish_claim(store,'gpu0',cell,dict(status='runtime_error',error='new failure'))
            self.assertIsNone(scheduler.claim_next(store,'gpu1'));self.assertEqual(len(store.records()),4)

    def test_fourth_failure_cannot_be_added_to_authorization(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan,failed_count=4)
            with self.assertRaises(ValueError):module.acknowledged_failures(store)

    def test_remaining381_profile_is_limited_to_the_three_known_keys_and_previous_session(self):
        module=self.module()
        self.assertIn('resume-20261027-c',module.RESUME_PROFILES)
        with patch.dict(os.environ,SCB_FIXED_SESSION='resume-20261027-c'):
            profile=module.resume_profile()
            self.assertEqual((profile['started'],profile['pending']),(499,381))
            self.assertEqual(profile['previous'],'parallel/sessions/resume-20261027-b')
            self.assertEqual(profile['keys'],{'9e26e7176ccc820d55761adf','88699a66c4c865a3cc78c8d0','a6def086abf1b1b0f74b46ef'})

    def test_concurrent_remaining_only_claims_keep_failure_and_old_stop(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan);before=(Path(td)/'attempts/0/result.json').read_bytes()
            context=multiprocessing.get_context('spawn');barrier=context.Barrier(2)
            children=[context.Process(target=consume,args=(td,plan,w,barrier)) for w in ('gpu0','gpu1')]
            for child in children:child.start()
            for child in children:child.join(25);self.assertEqual(child.exitcode,0)
            self.assertEqual(len(store.records()),12)
            self.assertEqual(sum(r['status']=='completed' for r in store.records()),11)
            self.assertEqual((Path(td)/'attempts/0/result.json').read_bytes(),before)
            self.assertEqual(json.loads((Path(td)/'parallel/stop.json').read_text()),{'key':'0'})
            state=json.loads((module.management_dir(td)/'queue.json').read_text())
            self.assertEqual(set(state['claims']),set(map(str,range(1,12))))

    def test_modified_acknowledged_result_and_wrong_plan_are_rejected(self):
        module=self.module();plan=fixture_plan()
        for variant in ('result','plan'):
            with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
                store=self.setup_session(td,plan)
                path=Path(td)/'attempts/0/result.json' if variant=='result' else module.management_dir(td)/'authorization.json'
                value=json.loads(path.read_text());value['plan_sha256']='changed';save(path,value)
                with self.assertRaises(ValueError):module.acknowledged_failures(store)

    def test_new_failure_still_stops_claims(self):
        module=self.module();scheduler=importlib.import_module('ops.fixed_study_parallel');plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan);cell=scheduler.claim_next(store,'gpu0')
            scheduler.finish_claim(store,'gpu0',cell,dict(status='runtime_error',error='new error'))
            self.assertIsNone(scheduler.claim_next(store,'gpu1'))
            self.assertEqual(len(store.records()),2)
            self.assertTrue((module.management_dir(td)/'stop.json').exists())

    def test_native_audit_remains_false_but_complete_expected_failure_coverage_can_pass(self):
        module=self.module();plan=fixture_plan()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,SCB_FIXED_SESSION='resume-test'):
            store=self.setup_session(td,plan)
            checked={'ok':False,'issues':['0: runtime_error'],'started':1,'required':12}
            self.assertFalse(module.coverage_audit(store,checked)['ok'])
            for cell in plan['cells'][1:]:store.claim(cell);store.finish(cell,dict(status='completed'))
            checked['started']=12
            self.assertTrue(module.coverage_audit(store,checked)['ok']);self.assertFalse(checked['ok'])
            checked['issues'].append('CSV score mismatch 1')
            self.assertFalse(module.coverage_audit(store,checked)['ok'])

    def test_session_path_traversal_rejected(self):
        module=self.module()
        for name in ('../old','/tmp','..','a/b'):
            with patch.dict(os.environ,SCB_FIXED_SESSION=name):
                with self.assertRaises(ValueError):module.management_dir('root')


if __name__=='__main__':unittest.main()
