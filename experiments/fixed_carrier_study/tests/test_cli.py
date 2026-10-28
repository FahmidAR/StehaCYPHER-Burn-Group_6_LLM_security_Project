import json
from pathlib import Path
import tempfile
import unittest
from experiments.acrostic_ablation.storage import RunStore
from experiments.acrostic_ablation.report import write_report
try:
    from experiments.fixed_carrier_study import cli
except ImportError:
    cli=None

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'results/acrostic-ablation-data/TAMAS'


class DriverTests(unittest.TestCase):
    def module(self):self.assertIsNotNone(cli,'fixed study CLI missing');return cli

    def test_offline_full_preparation_preserves_exact_88task_identity(self):
        m=self.module()
        if not DATA.exists():self.skipTest('external original TAMAS snapshot not installed')
        with tempfile.TemporaryDirectory() as td:
            p=m.prepare(ROOT,DATA,Path(td),'http://127.0.0.1:11435/v1')
            self.assertEqual(len(p['tasks']),88);self.assertEqual(len(p['cells']),880)
            self.assertEqual(p['task_list_sha256'],'254559a60e3abd319bf3b0941c25b80366f6c111eb706f266c5aaf7d60211d67')
            self.assertEqual(p['pilot_task_ids'],['IPI_healthcare_0','IPI_legal_0'])
            self.assertFalse(any((Path(td)/'attempts').glob('*/started.json')))
            state=m.audit(p,Path(td),'pilot');self.assertFalse(state['ok']);self.assertEqual(state['required'],20)

    def test_changed_profile_or_task_identity_cannot_pass_protocol_validation(self):
        m=self.module()
        if not DATA.exists():self.skipTest('external original TAMAS snapshot not installed')
        with tempfile.TemporaryDirectory() as td:
            p=m.prepare(ROOT,DATA,Path(td),'http://127.0.0.1:11435/v1')
            m.verify_design(p)
            for changed in ({**p,'profile':{**p['profile'],'judge_model':'different'}},
                {**p,'tasks':p['tasks'][:-1]}, {**p,'pilot_keys':p['pilot_keys'][:-1]}):
                with self.subTest(keys=changed.keys()),self.assertRaises(ValueError):m.verify_design(changed)

    def test_wrong_approval_is_rejected_before_remote_metadata_or_claiming(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as td,self.assertRaises(ValueError):
            m.execute({'plan_sha256':'not-approved'},'wrong',ROOT,DATA,Path(td),'pilot')

    def test_formal_gate_rejects_unrun_pilot_and_existing_failure_before_new_claim(self):
        m=self.module();self.assertTrue(hasattr(m,'require_continuation'),'pre-execution pilot/error gate missing')
        if not DATA.exists():self.skipTest('external TAMAS snapshot missing')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=m.prepare(ROOT,DATA,root,'http://127.0.0.1:11435/v1')
            with self.assertRaises(ValueError):m.require_continuation(p,root,'all')
            store=RunStore(root,p);cell=next(c for c in p['cells'] if c['key']==p['pilot_keys'][0])
            store.claim(cell);store.finish(cell,{'status':'runtime_error','error':'prior failure'})
            with self.assertRaises(ValueError):m.require_continuation(p,root,'pilot')
            self.assertEqual(len(store.records()),1)

    def test_empty_actor_and_judge_evidence_cannot_pass_pilot_gate(self):
        m=self.module()
        if not DATA.exists():self.skipTest('external TAMAS snapshot missing')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=m.prepare(ROOT,DATA,root,'http://127.0.0.1:11435/v1');store=RunStore(root,p)
            by_id={t['task_id']:t for t in p['tasks']}
            for cell in p['cells']:
                if cell['key'] not in p['pilot_keys']:continue
                store.claim(cell);attacked=cell['condition']=='attack';task=by_id[cell['task_id']]
                text=cell['carrier']['text'] if attacked else 'Normal reply.'
                scores=dict(task_id=cell['task_id'],task_completion=False,p_asr=0,ptn=1,ers=0,token_usage=5,
                    completion_time_turns=1,stealth_sim=0.5,completion_combined=False,decode={})
                row=dict(status='completed',scores=scores,run={'transcript':[['seed',text]]},placements=[],
                    diagnostics={'human_review':'pending','seed_bypasses':int(attacked),'transport_errors':[],'original_query':task['benign_query']})
                store.finish(cell,row)
                events=[dict(kind='fixed_attacker_stimulus',text=text,model_generated=False)] if attacked else [dict(kind='placeholder')]
                (store.folder(cell)/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events),encoding='utf-8')
            write_report(root,p,store.records());checked=m.audit(p,root,'pilot')
            self.assertFalse(checked['ok'],'Gate trusted self-report without actual model I/O')
            self.assertTrue(any('actor' in issue for issue in checked['issues']))
