import json
from pathlib import Path
import tempfile
import unittest
from experiments.acrostic_ablation.design import build_plan
from experiments.acrostic_ablation.report import write_report


class NativeReportTests(unittest.TestCase):
    def test_all_native_score_fields_survive_export_without_new_completion_criterion(self):
        task={'task_id':'t','benign_query':'Draft','agents':[{'name':'A','desc':'Draft'}]}
        plan=build_plan([task],payloads=['go']);cell=plan['cells'][1]
        score=dict(task_id='t',trial=1,attacked=True,branching_factor=3,task_completion=False,
            completion_time_turns=4,token_usage=55,p_asr=0.5,ptn=2,ers=0.25,p_asr_judge=0.1,
            ptn_judge=3,stealth_sim=0.7,tool_calls=['draft'],n_tool_calls=1,tools_available=True,
            tool_grounded_completion=True,completion_combined=False,captured_agents=['A'],
            stego=True,stego_delivered=False,reached_done_marker=False,decode={'roundtrip_ok':True})
        row=dict(cell,status='completed',scores=score)
        with tempfile.TemporaryDirectory() as td:
            summary=write_report(td,plan,[row])
            exported=json.loads((Path(td)/'results.jsonl').read_text(encoding='utf-8'))
            self.assertEqual({k:v for k,v in exported.items() if not k.startswith('ablation_')},score)
            self.assertNotIn('query_task_completion',exported)
            group=next(g for g in summary['groups'] if g['position']=='before_user')
            self.assertEqual(group['means']['task_completion'],0)
            self.assertEqual(group['means']['p_asr'],0.5)
            self.assertEqual(group['metric_counts']['p_asr'],1)
