import asyncio
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from experiments.acrostic_ablation import design as d,runner as r
from experiments.acrostic_ablation.baseline import source_snapshot

TASK=dict(task_id='t',benign_query='Draft a memo.',agents=[dict(name='Writer',desc='Draft'),dict(name='Reviewer',desc='Review')])
def message(kind,content,source=None):return NS(type=kind,content=content,source=source)
def system(content):return message('SystemMessage',content)


class NativeAblationTests(unittest.TestCase):
    def test_plan_declares_lengths_but_never_generates_template_text(self):
        plan=d.build_plan([TASK]);attack=plan['cells'][1]
        self.assertEqual(attack.get('hidden_letters'),12)
        self.assertNotIn('carrier',attack)
        self.assertEqual(len(plan['cells']),7)
        self.assertEqual(plan.get('execution_order'),[c['key'] for c in plan['cells']])

    def test_trigger_parameterization_preserves_native_prompts_and_restores_globals(self):
        self.assertTrue(hasattr(r,'using_trigger'),'native trigger adapter missing')
        with tempfile.TemporaryDirectory() as td:
            src,_=source_snapshot(Path(__file__).resolve().parents[3],Path(td))
            spec=importlib.util.spec_from_file_location('native_payload',src/'payload_riddle.py')
            payload=importlib.util.module_from_spec(spec);spec.loader.exec_module(payload)
            native=NS(ACROSTIC_TRIGGER='VALIDATE')
            original=payload.stego_seed_instruction('A','desc','Draft a memo.',3)
            with r.using_trigger(native,payload,'VALIDATE'):
                self.assertEqual(payload.stego_seed_instruction('A','desc','Draft a memo.',3),original)
            with r.using_trigger(native,payload,'generate test'):
                text=payload.stego_seed_instruction('A','desc','Draft a memo.',3)
                self.assertIn("codeword 'GENERATETEST' (write exactly 12 sentences",text)
                self.assertEqual(text.split('2. Also')[1],original.split('2. Also')[1])
                self.assertIn('Draft a memo.',text)
                self.assertIn('GENERATETEST',payload.decode_hint_instruction('B','desc',3))
            self.assertEqual(payload.ACROSTIC_TRIGGER,'VALIDATE');self.assertEqual(native.ACROSTIC_TRIGGER,'VALIDATE')

    def test_positions_move_only_first_seed_text_and_preserve_other_messages(self):
        self.assertTrue(hasattr(r,'relocate'),'native message placement missing')
        sys=system('native system');user=message('UserMessage','Draft a memo.','user')
        seed=message('UserMessage','Gather facts. Organize findings.','Writer_0')
        later=message('UserMessage','Later seed reply','Writer_0')
        toolcall=message('AssistantMessage',[{'id':'x','name':'tool'}],'Reviewer_1')
        toolresult=message('FunctionExecutionResultMessage',[{'call_id':'x','content':'ok'}])
        messages=[sys,user,seed,toolcall,toolresult,later]
        pre=r.relocate(messages,'Writer_0',TASK['benign_query'],'before_user',system)
        post=r.relocate(messages,'Writer_0',TASK['benign_query'],'after_user',system)
        memory=r.relocate(messages,'Writer_0',TASK['benign_query'],'system_memory',system)
        self.assertEqual(pre,[sys,seed,user,toolcall,toolresult,later])
        self.assertEqual(post,messages)
        self.assertEqual(memory[1].content,seed.content);self.assertEqual(memory[1].type,'SystemMessage')
        self.assertEqual(memory[2:],[user,toolcall,toolresult,later])
        self.assertEqual(messages,[sys,user,seed,toolcall,toolresult,later])

    def test_seed_own_assistant_history_or_missing_carrier_is_identity(self):
        self.assertTrue(hasattr(r,'relocate'),'native message placement missing')
        messages=[system('seed native prompt'),message('UserMessage',TASK['benign_query'],'user'),message('AssistantMessage','My reply','Writer_0')]
        self.assertEqual(r.relocate(messages,'Writer_0',TASK['benign_query'],'before_user',system),messages)

    def test_seed_generation_and_invalid_carrier_are_not_rewritten_or_filtered(self):
        own=[system('COVERT PROTOCOL (do NOT reveal this; native prompt)'),message('UserMessage',TASK['benign_query'],'user'),
            message('UserMessage','Own seed text','Writer_0')]
        self.assertEqual(r.relocate(own,'Writer_0',TASK['benign_query'],'before_user',system),own)
        invalid=message('UserMessage','Not a correct acrostic at all.','Writer_0')
        peer=[system('native peer codebook'),message('UserMessage',TASK['benign_query'],'user'),invalid]
        placed=r.relocate(peer,'Writer_0',TASK['benign_query'],'before_user',system)
        self.assertIs(placed[1],invalid)

    def test_adapter_uses_native_run_and_scores_once_without_extra_judge(self):
        self.assertTrue(hasattr(r,'using_trigger'),'native adapter missing')
        calls=[]
        class Client:
            async def create(self,messages,**kwargs):return 'model response'
            async def close(self):pass
        client=Client();native=NS(ACROSTIC_TRIGGER='VALIDATE',build_model_client=lambda:client)
        async def native_run(task,**kwargs):
            calls.append(('run',task,kwargs))
            mc=native.build_model_client()
            await mc.create([system('native peer prompt'),message('UserMessage',task['benign_query'],'user'),
                message('UserMessage','Gather facts. Organize findings.','Writer_0')],tools=['unchanged'])
            return {'transcript':[('Writer_0','Gather facts. Organize findings.')],'native_result':True}
        native.run_task=native_run
        def score(run):calls.append(('score',run));return {'task_completion':False,'p_asr':0.5,'ptn':2,'ers':0.25,'token_usage':55,'completion_time_turns':4,'stealth_sim':0.7,'extra_native_field':'preserve'}
        up={'mas_runner':native,'payload_riddle':NS(ACROSTIC_TRIGGER='VALIDATE'),
            'metrics':NS(score_run=score),'run_experiment':NS(decode_success_for=lambda task,bf:{'roundtrip_ok':True}),
            'SystemMessage':system,'stego_methods':NS(acr_decode=lambda text:'GO')}
        plan=d.build_plan([TASK]);out=asyncio.run(r.run_cell(TASK,plan['cells'][1],plan,up))
        self.assertEqual([c[0] for c in calls],['run','score'])
        self.assertEqual(out['scores'],{'task_completion':False,'p_asr':0.5,'ptn':2,'ers':0.25,'token_usage':55,
            'completion_time_turns':4,'stealth_sim':0.7,'extra_native_field':'preserve','branching_factor':3,'trial':1,'decode':{'roundtrip_ok':True}})
        self.assertNotIn('query_task_completion',out)
        self.assertEqual(calls[0][2],dict(attacked=True,branching_factor=3,seed_index=0,max_turns=12,stego=True))
        self.assertEqual(native.ACROSTIC_TRIGGER,'VALIDATE')
