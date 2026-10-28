import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import json
from experiments.acrostic_ablation.cli import prepare
from experiments.acrostic_ablation.design import SCHEMA,build_plan
from experiments.acrostic_ablation.storage import sign_plan,save


class GateTests(unittest.TestCase):
    def test_execute_without_approval_fails_before_optional_framework_imports(self):
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,'-m','experiments.acrostic_ablation.cli','--execute','--output',td],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn('approval',p.stderr.lower())
            self.assertNotIn('ModuleNotFoundError',p.stderr)
            self.assertFalse((Path(td)/'attempts').exists())

    def test_preparation_never_calls_template_or_extra_control_api(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);data=root/'TAMAS/data/DPI';data.mkdir(parents=True)
            (data/'education_tasks.json').write_text(json.dumps([{'user query':'Draft a memo.',
                'agents':[{'agent_name':'A','agent_description':'Draft'}]}]),encoding='utf-8')
            plan=prepare(Path(__file__).resolve().parents[3],root/'TAMAS',root/'out',['go'],1,1,'http://127.0.0.1:11434/v1')
            self.assertEqual(plan['schema'],SCHEMA);self.assertEqual(len(plan['cells']),4)
            self.assertFalse((root/'out/attempts').exists())

    def test_superseded_template_plan_cannot_execute_even_with_its_sha(self):
        with tempfile.TemporaryDirectory() as td:
            plan=build_plan([dict(task_id='t',benign_query='Draft',agents=[dict(name='A',desc='Draft')])])
            plan['schema']='acrostic-length-position-v1';plan=sign_plan(plan);save(Path(td)/'plan.json',plan)
            p=subprocess.run([sys.executable,'-m','experiments.acrostic_ablation.cli','--execute','--approved-plan-sha',plan['plan_sha256'],
                '--output',td],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('superseded',p.stderr.lower())
            self.assertNotIn('ModuleNotFoundError',p.stderr)

