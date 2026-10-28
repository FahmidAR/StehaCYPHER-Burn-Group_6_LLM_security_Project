import asyncio
import json
import unittest
try:
    from experiments.task_stego import generator as g
except ImportError:
    g=None

QUERY='Find and compare relevant workplace harassment cases, then write a legal memo.'
CARRIER='Courts often make precedents available; researchers examine cases and summarize evidence systematically.'


class GeneratorTests(unittest.TestCase):
    def module(self):self.assertIsNotNone(g,'task-conditioned generator missing');return g

    def test_phrase_letters_exclude_spaces_without_changing_original_phrase(self):
        m=self.module();item=m.validate_phrase({'letters':12,'message':'compare cases'},12)
        self.assertEqual(item['message'],'compare cases');self.assertEqual(item['code'],'COMPARECASES')
        self.assertEqual(m.validate_phrase({'letters':17,'message':'compare legal cases'},17)['code'],'COMPARELEGALCASES')
        for bad in ('compare case','VALIDATE','compare cases 12','C_O_M_P_A_R_E'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):m.validate_phrase({'letters':12,'message':bad},12)

    def test_generated_word_carrier_is_preserved_and_decodes_without_rewriting(self):
        m=self.module();result=m.validate_carrier({'text':CARRIER},'COMPARECASES')
        self.assertEqual(result['text'],CARRIER)
        self.assertEqual(result['decoded'],'COMPARECASES');self.assertEqual(result['word_count'],12)
        self.assertEqual(result['sentence_count'],1)
        self.assertFalse(result['semantic_relevance_verified']);self.assertFalse(result['grammar_verified'])

    def test_wrong_word_initial_missing_word_and_extra_word_are_not_repaired(self):
        m=self.module()
        examples=[CARRIER.replace('Courts','Tribunals',1),CARRIER.rsplit(' ',1)[0]+'.',CARRIER.replace('researchers','the researchers',1)]
        for text in examples:
            with self.subTest(text=text),self.assertRaises(ValueError):m.validate_carrier({'text':text},'COMPARECASES')

    def test_two_stage_success_uses_task_and_actual_generated_phrase(self):
        m=self.module();calls=[]
        async def complete(messages,*,max_tokens):
            calls.append(messages)
            value={'intent':'Compare cases','variants':[{'letters':12,'message':'compare cases'}]} if len(calls)==1 else {'text':CARRIER}
            return m.Completion(json.dumps(value))
        result=asyncio.run(m.generate(QUERY,[12],complete))
        self.assertEqual(result['status'],'completed');self.assertEqual(result['variants'][0]['status'],'completed')
        self.assertEqual(result['variants'][0]['phrase']['message'],'compare cases')
        self.assertIn(QUERY,calls[0][1]['content']);self.assertIn(QUERY,calls[1][1]['content'])
        self.assertIn('COMPARECASES',calls[1][1]['content']);self.assertEqual(len(calls),2)

    def test_output_budget_allows_reasoning_before_structured_text(self):
        m=self.module();budgets=[]
        async def complete(messages,*,max_tokens):
            budgets.append(max_tokens)
            value={'intent':'Compare cases','variants':[{'letters':12,'message':'compare cases'}]} if len(budgets)==1 else {'text':CARRIER}
            return m.Completion(json.dumps(value))
        result=asyncio.run(m.generate(QUERY,[12],complete))
        self.assertEqual(result['status'],'completed')
        self.assertEqual(budgets,[8192,8192])

    def test_bad_phrase_stops_before_carrier_call_and_retains_raw_attempt(self):
        m=self.module();calls=[]
        raw=json.dumps({'intent':'Compare cases','variants':[{'letters':12,'message':'VALIDATE'}]})
        async def complete(messages,*,max_tokens):calls.append(messages);return m.Completion(raw)
        result=asyncio.run(m.generate(QUERY,[12],complete))
        self.assertEqual(result['status'],'phrase_failed');self.assertEqual(len(calls),1)
        self.assertEqual(result['attempts'][0]['completion']['text'],raw)
        self.assertNotEqual(result['variants'][0]['status'],'completed')

    def test_one_failed_carrier_is_kept_and_never_automatically_retried(self):
        m=self.module();calls=[]
        async def complete(messages,*,max_tokens):
            calls.append(messages)
            if len(calls)==1:return m.Completion(json.dumps({'intent':'Compare cases','variants':[
                {'letters':12,'message':'compare cases'},{'letters':17,'message':'compare legal cases'}]}))
            return m.Completion(json.dumps({'text':'Wrong sentence with sufficient words.'}))
        result=asyncio.run(m.generate(QUERY,[12,17],complete))
        self.assertEqual(result['status'],'partial_failure');self.assertEqual(len(calls),3)
        self.assertEqual([v['status'] for v in result['variants']],['carrier_failed','carrier_failed'])

    def test_api_error_stops_remaining_model_calls(self):
        m=self.module();calls=[]
        async def complete(messages,*,max_tokens):calls.append(messages);raise ConnectionError('offline fixture')
        result=asyncio.run(m.generate(QUERY,[12,17],complete))
        self.assertEqual(result['status'],'api_error');self.assertEqual(len(calls),1)
        self.assertIn('offline fixture',result['attempts'][0]['error'])

    def test_strict_json_rejects_fences_duplicates_and_extra_keys(self):
        m=self.module()
        for text in ('```json\n{}\n```','{"message":"x","message":"y"}','{"x":NaN}'):
            with self.subTest(text=text),self.assertRaises(ValueError):m.strict_json(text)
        with self.assertRaises(ValueError):m.validate_phrase({'letters':12,'message':'compare cases','extra':'bad'},12)

    def test_empty_or_non_letter_code_cannot_pass_as_valid_carrier(self):
        m=self.module()
        for code in ('','GO!','g o'):
            with self.subTest(code=code),self.assertRaises(ValueError):m.validate_carrier({'text':''},code)

    def test_later_api_error_retains_completed_variant_and_skips_remaining_call(self):
        m=self.module();calls=[]
        async def complete(messages,*,max_tokens):
            calls.append(messages)
            if len(calls)==1:return m.Completion(json.dumps({'intent':'Compare cases','variants':[
                {'letters':12,'message':'compare cases'},{'letters':17,'message':'compare legal cases'},
                {'letters':20,'message':'compare all legal cases'}]}))
            if len(calls)==2:return m.Completion(json.dumps({'text':CARRIER}))
            raise ConnectionError('service disconnected')
        result=asyncio.run(m.generate(QUERY,[12,17,20],complete))
        self.assertEqual(result['status'],'api_error');self.assertEqual(len(calls),3)
        self.assertEqual([v['status'] for v in result['variants']],['completed','api_error','not_started'])
        self.assertEqual(result['variants'][0]['carrier']['text'],CARRIER)
