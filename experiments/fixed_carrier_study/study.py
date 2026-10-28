"""880-cell same88-task design; pilot20 is an ordered subset of the same keys."""
from experiments.acrostic_ablation.design import build_plan as native_plan,digest
from .catalog import PAYLOADS,get_carrier

SCHEMA='fixed-word-carrier-length-position-v1'
EXPECTED_TASK_SHA='254559a60e3abd319bf3b0941c25b80366f6c111eb706f266c5aaf7d60211d67'


def build_plan(tasks):
    plan=native_plan(tasks,PAYLOADS,1);plan['schema']=SCHEMA
    by_id={t['task_id']:t for t in tasks}
    for cell in plan['cells']:
        cell.pop('key');cell['study_schema']=SCHEMA
        cell['carrier']=get_carrier(by_id[cell['task_id']]['domain'],cell['payload']) if cell['condition']=='attack' else None
        cell['key']=digest(cell)[:24]
    pilot_ids=[next(t['task_id'] for t in tasks if t['domain']==d) for d in ('healthcare','legal')]
    plan['pilot_task_ids']=pilot_ids
    plan['pilot_keys']=[c['key'] for c in plan['cells'] if c['task_id'] in pilot_ids]
    plan['execution_order']=plan['pilot_keys']+[c['key'] for c in plan['cells'] if c['key'] not in plan['pilot_keys']]
    plan['task_list_sha256']=digest(tasks)
    plan['warnings']=[
        'Controlled preauthored attacker stimulus, not autonomous natural-text generation; semantic/human review pending.',
        'First seed response is an explicit fixed stimulus with zero model API usage; all later responses use the native model.',
        'Native score_run is unchanged, including first-actor task reference, char/4 tokens and transcript-item turns.',
        'Native stego_delivered still uses sentence decoding; fixed word roundtrip/exposure are separate diagnostics.',
        'Original GO synonym-codec decode control is preserved, not a word-acrostic model decode score.',
        'Different lengths also change lexical content; system_memory also changes authority, not just position.']
    return plan


def phase_keys(plan,phase):
    if phase=='pilot':return plan['pilot_keys']
    if phase=='all':return plan['execution_order']
    raise ValueError('Unknown execution phase')
