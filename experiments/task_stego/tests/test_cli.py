import json
import asyncio
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
try:
    from experiments.task_stego import cli
except ImportError:
    cli=None


class CliTests(unittest.TestCase):
    def test_contradictory_ranged_protocol_is_rejected_before_started_marker(self):
        async def no_network(plan,sink):return {'status':'completed','variants':[]}
        for key,value in [('model','other:model'),('max_output_tokens_per_request',1),('api_retries',2),('timeout',1)]:
            with self.subTest(field=key),tempfile.TemporaryDirectory() as td:
                root=Path(td)
                original=cli.prepare_ranged('Compare cases.',root/'original','http://127.0.0.1:11434/v1')
                altered=cli.sign_plan({**original,key:value})
                with patch.object(cli,'generate_approved',new=no_network),self.assertRaisesRegex(ValueError,'protocol'):
                    cli.execute(altered,altered['plan_sha256'],root/'altered')
                self.assertFalse((root/'altered/started.json').exists())

    def test_ranged_cli_freezes_bands_repairs_and_total_budget_without_calls(self):
        with tempfile.TemporaryDirectory() as td:
            proc=subprocess.run([sys.executable,'-m','experiments.task_stego.cli','--request','Compare legal cases.',
                '--ranged','--max-repairs','2','--output',td],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            plan=json.loads((Path(td)/'plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['schema'],'task-related-ranged-word-stego-v3')
            self.assertEqual(plan['reasoning_effort'],'none');self.assertEqual(plan['max_model_requests'],12)
            self.assertEqual([(b['min_letters'],b['max_letters']) for b in plan['bands']],[(4,8),(9,14),(15,24)])
            self.assertIn('task_stego/ranged.py',plan['code_sha256'])
            self.assertFalse((Path(td)/'started.json').exists())

    def test_ranged_runtime_dispatches_word_array_generator_not_exact_sentence_generator(self):
        from experiments.task_stego.tests.test_ranged import PHRASES,WORDS4,WORDS12,WORDS17
        replies=[PHRASES,{'words':WORDS4},{'words':WORDS12},{'words':WORDS17}];calls=[];events=[]
        class Reply:
            def __init__(self,value):self.value=value
            def model_dump(self,**kwargs):return {'choices':[{'message':{'content':json.dumps(self.value)},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':30,'completion_tokens':15,'total_tokens':45}}
        class Client:
            def __init__(self,**kwargs):self.chat=NS(completions=NS(create=self.create))
            async def create(self,**kwargs):calls.append(kwargs);return Reply(replies[len(calls)-1])
            async def close(self):pass
        with tempfile.TemporaryDirectory() as td:
            self.assertTrue(hasattr(cli,'prepare_ranged'),'ranged plan preparation missing')
            plan=cli.prepare_ranged('Compare legal cases.',Path(td),'http://127.0.0.1:11434/v1')
            with patch.dict(sys.modules,{'openai':NS(AsyncOpenAI=Client)}), \
                 patch('urllib.request.urlopen',return_value=io.StringIO(json.dumps({'models':[{'name':'qwen3.5:35b'}]}))), \
                 patch('importlib.metadata.version',return_value='offline-fixture'):
                result=asyncio.run(cli.generate_approved(plan,events.append))
            self.assertEqual(result['status'],'completed');self.assertEqual(result['model_requests'],4)
            self.assertEqual([v['carrier']['word_count'] for v in result['variants']],[4,12,17])
            self.assertEqual(result['variants'][1]['carrier']['sentence_count'],2)
            self.assertTrue(all(c['reasoning_effort']=='none' for c in calls))
            with self.assertRaises(ValueError):cli.execute(plan,'wrong',Path(td))
            self.assertFalse((Path(td)/'started.json').exists())

    def test_disabled_thinking_is_forwarded_to_each_generation_request(self):
        # Omitting the request-level control caused reasoning-only, empty answers.
        for effort in ('none',None):
            with self.subTest(reasoning_effort=effort),tempfile.TemporaryDirectory() as td:
                plan=cli.prepare('Assess similar legal evidence.',[4],Path(td),'http://127.0.0.1:11434/v1')
                plan['reasoning_effort']=effort
                calls=[];events=[]
                texts=[json.dumps({'intent':'Review a case','variants':[{'letters':4,'message':'Case'}]}),
                    json.dumps({'text':'Courts assess similar evidence.'})]
                class Reply:
                    def __init__(self,text):self.text=text
                    def model_dump(self,**kwargs):return {'choices':[{'message':{'content':self.text},'finish_reason':'stop'}],
                        'usage':{'prompt_tokens':30,'completion_tokens':15,'total_tokens':45}}
                class Client:
                    def __init__(self,**kwargs):self.chat=NS(completions=NS(create=self.create))
                    async def create(self,**kwargs):
                        calls.append(kwargs);return Reply(texts[len(calls)-1])
                    async def close(self):pass
                with patch.dict(sys.modules,{'openai':NS(AsyncOpenAI=Client)}), \
                     patch('urllib.request.urlopen',return_value=io.StringIO(json.dumps({'models':[{'name':'qwen3.5:35b'}]}))), \
                     patch('importlib.metadata.version',return_value='offline-fixture'):
                    result=asyncio.run(cli.generate_approved(plan,events.append))
                self.assertEqual(result['status'],'completed');self.assertEqual(len(calls),2)
                self.assertEqual(result['variants'][0]['carrier']['decoded'],'CASE')
                for call in calls:
                    if effort is None:self.assertNotIn('reasoning_effort',call)
                    else:self.assertEqual(call.get('reasoning_effort'),'none')
                    self.assertNotIn('temperature',call);self.assertEqual(call['max_tokens'],8192)

    def test_offline_cli_freezes_explicit_no_thinking_setting(self):
        with tempfile.TemporaryDirectory() as td:
            proc=subprocess.run([sys.executable,'-m','experiments.task_stego.cli','--request','Assess legal evidence.',
                '--letters','4','--reasoning-effort','none','--output',td],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            plan=json.loads((Path(td)/'plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['reasoning_effort'],'none')
            self.assertFalse((Path(td)/'started.json').exists())

    def test_no_execution_approval_means_no_model_import_or_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            proc=subprocess.run([sys.executable,'-m','experiments.task_stego.cli','--execute','--output',td],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0);self.assertIn('approval',proc.stderr.lower())
            self.assertNotIn('ModuleNotFoundError',proc.stderr);self.assertFalse((Path(td)/'started.json').exists())

    def test_offline_prepare_builds_plan_only_and_rejects_changed_request(self):
        self.assertIsNotNone(cli,'offline generator CLI missing')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            plan=cli.prepare('Compare the legal cases.',[12,17],root,'http://127.0.0.1:11434/v1')
            self.assertEqual(plan['max_model_requests'],3)
            self.assertEqual(plan['lengths'],[12,17]);self.assertEqual(plan['model'],'qwen3.5:35b')
            self.assertFalse((root/'started.json').exists());self.assertFalse((root/'result.json').exists())
            self.assertEqual(json.loads((root/'plan.json').read_text(encoding='utf-8')),plan)
            with self.assertRaises(ValueError):cli.prepare('A different request.',[12,17],root,'http://127.0.0.1:11434/v1')

    def test_wrong_sha_and_already_started_block_before_model_loading(self):
        self.assertIsNotNone(cli,'generator CLI missing')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan=cli.prepare('Compare legal cases.',[12],root,'http://127.0.0.1:11434/v1')
            with self.assertRaises(ValueError):cli.execute(plan,'wrong',root)
            (root/'started.json').write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError):cli.execute(plan,plan['plan_sha256'],root)
            self.assertFalse((root/'result.json').exists())

    def test_sentence_plan_is_rejected_before_any_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan=cli.prepare('Compare legal cases.',[12],root,'http://127.0.0.1:11434/v1')
            old=cli.sign_plan({**plan,'schema':'task-related-stego-generator-v1'})
            with self.assertRaisesRegex(ValueError,'sentence-acrostic'):cli.execute(old,old['plan_sha256'],root)
            self.assertFalse((root/'started.json').exists())

    def test_malformed_api_envelope_retains_raw_body_and_usage_before_stopping(self):
        self.assertIsNotNone(cli,'generator CLI missing')
        raw={'id':'broken-response','model':'qwen3.5:35b','choices':[],
            'usage':{'prompt_tokens':41,'completion_tokens':7,'total_tokens':48}}
        calls=[];events=[]
        class Reply:
            choices=[]
            def model_dump(self,**kwargs):return raw
        class Client:
            def __init__(self,**kwargs):self.chat=NS(completions=NS(create=self.create))
            async def create(self,**kwargs):calls.append(kwargs);return Reply()
            async def close(self):pass
        plan={'request':'Compare legal cases.','lengths':[12,17],'model':'qwen3.5:35b',
            'base_url':'http://127.0.0.1:11434/v1','timeout':300,'max_model_requests':3}
        with patch.dict(sys.modules,{'openai':NS(AsyncOpenAI=Client)}), \
             patch('urllib.request.urlopen',return_value=io.StringIO(json.dumps({'models':[{'name':'qwen3.5:35b'}]}))), \
             patch('importlib.metadata.version',return_value='offline-fixture'):
            result=asyncio.run(cli.generate_approved(plan,events.append))
        self.assertEqual(result['status'],'api_error');self.assertEqual(len(calls),1)
        self.assertEqual(result['model_requests'],1)
        self.assertEqual(result['attempts'][0].get('raw_response'),raw)
        self.assertTrue(any(e.get('response')==raw for e in events))
