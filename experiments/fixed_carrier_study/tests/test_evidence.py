import copy
import unittest
from experiments.fixed_carrier_study.catalog import get_carrier
try:
    from experiments.fixed_carrier_study.evidence import check_events
except ImportError:check_events=None


class EvidenceTests(unittest.TestCase):
    def fixture(self):
        self.assertIsNotNone(check_events,'actual input evidence checker missing')
        carrier=get_carrier('legal','review');task={'benign_query':'Original request.','agents':[{'name':'Seed'}]}
        cell={'condition':'attack','position':'before_user','carrier':carrier}
        system={'type':'SystemMessage','content':'TEAM CODEBOOK'}
        user={'type':'UserMessage','content':'Original request.','source':'user'}
        seed={'type':'UserMessage','content':carrier['text'],'source':'Seed_0'}
        events=[{'kind':'fixed_attacker_stimulus','source':'Seed_0','text':carrier['text'],'model_generated':False,
            'messages':[{'type':'SystemMessage','content':'COVERT PROTOCOL (do NOT reveal this;)'},user],
            'model_api_usage':{'prompt_tokens':0,'completion_tokens':0}},
            {'kind':'native_actor_input','original_messages':[system,user,seed],'messages':[system,seed,user]},
            {'kind':'native_actor_output','response':{'content':'Peer reply.','finish_reason':'stop'}}]
        for prefix in ('You judge whether','You judge ONE','You compare an agent transcript'):
            events.extend([{'kind':'native_judge_input','request':{'messages':[{'role':'system','content':prefix},{'role':'user','content':'Evidence'}]}},
                {'kind':'native_judge_output','response':{'choices':[{'finish_reason':'stop','message':{'content':'NO'}}]}}])
        row={'diagnostics':{'actor_outer_calls':1,'peer_exposures':1},'placements':[{'carrier':carrier['text']}],
            'run':{'transcript':[['Seed_0',carrier['text']]]}}
        return task,cell,row,events

    def test_actual_exposure_and_complete_io_can_pass(self):
        task,cell,row,events=self.fixture();self.assertEqual(check_events(task,cell,row,events),[])

    def test_swapped_position_changed_query_missing_peer_or_output_are_rejected(self):
        task,cell,row,events=self.fixture()
        cases=[]
        changed=copy.deepcopy(events);changed[1]['messages'][1:]=reversed(changed[1]['messages'][1:]);cases.append(changed)
        changed=copy.deepcopy(events);changed[1]['messages'][-1]['content']='Changed request.';cases.append(changed)
        changed=copy.deepcopy(events);changed[1]['original_messages'].pop();changed[1]['messages']=changed[1]['original_messages'];cases.append(changed)
        cases.append([e for e in events if e['kind']!='native_actor_output'])
        cases.append([e for e in events if e['kind']!='native_judge_output'])
        for changed in cases:
            with self.subTest(events=changed):self.assertTrue(check_events(task,cell,row,changed))
