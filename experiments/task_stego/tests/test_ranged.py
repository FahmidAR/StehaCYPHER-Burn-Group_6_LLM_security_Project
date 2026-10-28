import asyncio
import json
import unittest
from experiments.task_stego.generator import Completion,InvalidCompletion
try:
    from experiments.task_stego import ranged as r
except ImportError:
    r=None

BANDS=[{'label':'short','min_letters':4,'max_letters':8},
    {'label':'medium','min_letters':9,'max_letters':14},
    {'label':'long','min_letters':15,'max_letters':24}]
PHRASES={'intent':'Compare cases','variants':[{'label':'short','message':'case'},
    {'label':'medium','message':'compare cases'},{'label':'long','message':'compare legal cases'}]}
WORDS4=['Courts','assess','similar','evidence.']
WORDS12=['Courts','often','make','precedents','available.','Researchers','examine','cases','and','summarize','evidence','systematically.']
WORDS17=['Courts','often','make','precedents','available;','researchers','examine','legal','evidence,','gather','arguments,','link','citations','and','summarize','evidence','systematically.']


class RangedTests(unittest.TestCase):
    def module(self):self.assertIsNotNone(r,'ranged word generator missing');return r

    def test_bands_reject_overlap_reversal_boolean_and_duplicate_label(self):
        m=self.module();self.assertEqual(m.validate_bands(BANDS),None)
        bads=[[BANDS[1],BANDS[0]],[BANDS[0],{**BANDS[1],'min_letters':8}],
            [{**BANDS[0],'max_letters':True}],[{**BANDS[0],'min_letters':9}],
            [BANDS[0],{**BANDS[1],'label':'short'}],[],BANDS+[{'label':'extra','min_letters':25,'max_letters':30}]]
        for bad in bads:
            with self.subTest(bad=bad),self.assertRaises(ValueError):m.validate_bands(bad)

    def test_phrases_use_actual_band_lengths_not_model_claimed_counts(self):
        m=self.module();intent,phrases=m.validate_phrases(PHRASES,BANDS)
        self.assertEqual(intent,'Compare cases')
        self.assertEqual([p['hidden_letters'] for p in phrases],[4,12,17])
        self.assertEqual([p['code'] for p in phrases],['CASE','COMPARECASES','COMPARELEGALCASES'])
        for bad in ({'intent':'x','variants':[{'label':'short','message':'too long for the band'}]},
                    {'intent':'x','variants':[{'label':'short','message':'ca se2'}]},
                    {'intent':'x','variants':[{'label':'short','message':'case','letters':4}]}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):m.validate_phrases(bad,[BANDS[0]])

    def test_paragraph_can_have_two_sentences_with_all_words_counted(self):
        m=self.module();result=m.validate_paragraph({'words':WORDS12},'COMPARECASES')
        self.assertEqual(result['text'],'Courts often make precedents available. Researchers examine cases and summarize evidence systematically.')
        self.assertEqual(result['decoded'],'COMPARECASES');self.assertEqual(result['word_count'],12)
        self.assertEqual(result['sentence_count'],2);self.assertFalse(result['grammar_verified'])
        self.assertFalse(result['semantic_relevance_verified'])

    def test_extra_function_word_is_rejected_and_original_words_are_not_modified(self):
        m=self.module();words=['Courts','assess','the','similar','evidence.'];before=words.copy()
        detail=m.carrier_errors({'words':words},'CASE')
        self.assertEqual(detail['actual_word_count'],5)
        self.assertEqual(detail['actual_initials'],'CATSE')
        self.assertEqual(detail['positions'][0],{'position':3,'expected':'S','actual':'T','word':'the'})
        self.assertEqual(words,before)
        with self.assertRaises(ValueError):m.validate_paragraph({'words':words},'CASE')

    def test_multiword_entries_and_missing_final_punctuation_cannot_pass(self):
        m=self.module()
        for value in ({'words':['Courts assess','similar','evidence.']},
            {'words':['Courts','assess','similar','evidence']}, {'text':'Courts assess similar evidence.'},
            {'words':['Courts','assess','similar','evidence.'],'extra':True}):
            with self.subTest(value=value),self.assertRaises(ValueError):m.validate_paragraph(value,'CASE')

    def test_standalone_letter_padding_is_rejected_but_a_and_i_are_allowed(self):
        m=self.module()
        # Live smoke produced a final 's.' to satisfy a slot; matching initials is insufficient.
        with self.assertRaises(ValueError):m.validate_paragraph({'words':['Courts','assess','similar','s.']},'CASS')
        self.assertEqual(m.validate_paragraph({'words':['A','case','is','evidence.']},'ACIE')['decoded'],'ACIE')
        self.assertEqual(m.validate_paragraph({'words':['I','assess','similar','evidence.']},'IASE')['decoded'],'IASE')

    def test_feedback_repairs_only_failed_carrier_and_keeps_every_attempt(self):
        m=self.module();calls=[];replies=[PHRASES,{'words':['Wrong.']},{'words':WORDS4},
            {'words':WORDS12},{'words':WORDS17}]
        async def complete(messages,*,max_tokens):
            calls.append(messages);return Completion(json.dumps(replies[len(calls)-1]))
        result=asyncio.run(m.generate_ranges('Compare legal cases.',BANDS,complete,max_repairs=2))
        self.assertEqual(result['status'],'completed');self.assertEqual(len(calls),5)
        self.assertEqual(len(result['attempts']),5)
        self.assertEqual(result['attempts'][1]['validation_status'],'rejected')
        self.assertEqual(result['attempts'][2]['validation_status'],'accepted')
        feedback=json.loads(calls[2][-1]['content'])
        self.assertEqual(feedback['mechanical_errors']['actual_word_count'],1)
        self.assertEqual(feedback['mechanical_errors']['expected_initials'],'CASE')
        self.assertEqual(result['variants'][0]['carrier']['words'],WORDS4)
        self.assertFalse(result['same_intent_verified']);self.assertEqual(result['human_review'],'pending')

    def test_phrase_repair_keeps_failure_then_uses_actual_valid_phrases(self):
        m=self.module();calls=[]
        replies=[{'intent':'Compare cases','variants':[{'label':'short','message':'far too many letters'}]},
            {'intent':'Compare cases','variants':[{'label':'short','message':'case'}]},{'words':WORDS4}]
        async def complete(messages,*,max_tokens):
            calls.append(messages);return Completion(json.dumps(replies[len(calls)-1]))
        result=asyncio.run(m.generate_ranges('Compare cases.',[BANDS[0]],complete,max_repairs=1))
        self.assertEqual(result['status'],'completed');self.assertEqual(len(calls),3)
        self.assertEqual(result['attempts'][0]['validation_status'],'rejected')
        self.assertIn('CASE',calls[-1][1]['content'])

    def test_exhausted_repair_is_failure_not_silently_retried(self):
        m=self.module();calls=[]
        async def complete(messages,*,max_tokens):
            calls.append(messages)
            return Completion(json.dumps(PHRASES if len(calls)==1 else {'words':['Wrong.']}))
        result=asyncio.run(m.generate_ranges('Compare cases.',BANDS,complete,max_repairs=2))
        self.assertEqual(len(calls),10);self.assertEqual(result['status'],'partial_failure')
        self.assertTrue(all(v['status']=='carrier_failed' for v in result['variants']))
        self.assertEqual(sum(a['validation_status']=='rejected' for a in result['attempts']),9)

    def test_api_failure_preserves_raw_usage_and_previous_success(self):
        m=self.module();calls=[];raw={'choices':[],'usage':{'prompt_tokens':9,'completion_tokens':7,'total_tokens':16}}
        async def complete(messages,*,max_tokens):
            calls.append(messages)
            if len(calls)==1:return Completion(json.dumps(PHRASES))
            if len(calls)==2:return Completion(json.dumps({'words':WORDS4}))
            raise InvalidCompletion('broken envelope',raw)
        result=asyncio.run(m.generate_ranges('Compare cases.',BANDS,complete))
        self.assertEqual(len(calls),3);self.assertEqual(result['status'],'api_error')
        self.assertEqual([v['status'] for v in result['variants']],['completed','api_error','not_started'])
        self.assertEqual(result['attempts'][-1]['raw_response'],raw)

    def test_invalid_repair_limit_makes_no_request(self):
        m=self.module()
        async def forbidden(*args,**kwargs):self.fail('must validate before request')
        for limit in (-1,3,True):
            with self.subTest(limit=limit),self.assertRaises(ValueError):
                asyncio.run(m.generate_ranges('Compare cases.',BANDS,forbidden,max_repairs=limit))

    def test_http_error_retains_status_body_text_and_request_id(self):
        from types import SimpleNamespace
        m=self.module();events=[]
        class HttpFailure(Exception):
            status_code=500
            body={'error':'backend failure','usage':{'prompt_tokens':9,'completion_tokens':7,'total_tokens':16}}
            response=SimpleNamespace(text='{"error":"backend failure","usage":{"total_tokens":16}}')
            request_id='test-request-1'
        async def complete(messages,*,max_tokens):raise HttpFailure('backend failure')
        result=asyncio.run(m.generate_ranges('Compare cases.',BANDS,complete,sink=events.append))
        self.assertEqual(result['status'],'api_error');self.assertEqual(len(result['attempts']),1)
        evidence=result['attempts'][0].get('raw_response')
        self.assertIsNotNone(evidence,'HTTP evidence was discarded')
        self.assertEqual(evidence['status_code'],500);self.assertEqual(evidence['body'],HttpFailure.body)
        self.assertEqual(evidence['response_text'],HttpFailure.response.text)
        self.assertEqual(evidence['request_id'],'test-request-1')
        self.assertEqual(events[-1]['raw_response'],evidence)
