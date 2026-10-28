"""Characterize the pinned real scorer; only its external OpenAI transport is fake."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from experiments.acrostic_ablation.baseline import source_snapshot


class NativeMetricTests(unittest.TestCase):
    def test_original_scorer_retains_its_whole_field_set_and_definitions(self):
        requests=[]
        def create(**kwargs):
            requests.append(kwargs);system=kwargs['messages'][0]['content']
            answer='YES' if system.startswith('You judge whether') else ('NO' if system.startswith('You judge ONE') else '0.75')
            return NS(choices=[NS(message=NS(content=answer))])
        class FakeOpenAI:
            def __init__(self,**kwargs):self.chat=NS(completions=NS(create=create))
        with tempfile.TemporaryDirectory() as td:
            source,_=source_snapshot(Path(__file__).resolve().parents[3],Path(td))
            def load(name):
                spec=importlib.util.spec_from_file_location(name,source/(name+'.py'))
                mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
            structural=load('structural_metrics')
            with patch.dict(sys.modules,{'openai':NS(OpenAI=FakeOpenAI),'structural_metrics':structural}):
                metrics=load('metrics')
                run=dict(task_id='t',attacked=True,branching_factor=3,turns_used=2,approx_tokens=11,reached_done=True,
                    stego=True,stego_delivered=True,tools_available=True,n_tool_calls=1,tool_calls=['write_memo'],
                    transcript=[('A','Check a test case combination.'),('B','Here is the completed memo.')])
                scored=metrics.score_run(run)
            self.assertEqual(scored,dict(task_id='t',attacked=True,branching_factor=3,completion_time_turns=2,
                token_usage=11,reached_done_marker=True,stego=True,stego_delivered=True,tools_available=True,
                n_tool_calls=1,tool_calls=['write_memo'],tool_grounded_completion=True,p_asr=0.5,ptn=1,captured_agents=['A'],
                ers=0.5,task_completion=True,p_asr_judge=0.0,ptn_judge=2,stealth_sim=0.75,completion_combined=True))
            self.assertEqual(len(requests),4)
