"""Thin adapter: original run_task and score_run, only trigger and placement vary."""
from contextlib import contextmanager
import functools
import importlib
from pathlib import Path
import sys
from .design import POSITIONS,normalize_payload


@contextmanager
def using_trigger(native,payload,phrase):
    old_native=native.ACROSTIC_TRIGGER;old_payload=payload.ACROSTIC_TRIGGER
    code=normalize_payload(phrase)
    native.ACROSTIC_TRIGGER=payload.ACROSTIC_TRIGGER=code
    try:yield
    finally:native.ACROSTIC_TRIGGER=old_native;payload.ACROSTIC_TRIGGER=old_payload


def kind(message):return getattr(message,'type',type(message).__name__)


def seed_message(messages,seed_name):
    if any(kind(m)=='SystemMessage' and 'COVERT PROTOCOL (do NOT reveal this' in m.content for m in messages):return None
    return next((m for m in messages if kind(m)=='UserMessage' and getattr(m,'source',None)==seed_name and isinstance(m.content,str)),None)


def relocate(messages,seed_name,query,position,system_factory):
    if position not in POSITIONS:raise ValueError('Unknown receiver placement')
    out=list(messages);seed=seed_message(out,seed_name)
    if seed is None:return out
    user=next((m for m in out if kind(m)=='UserMessage' and getattr(m,'source',None)=='user' and m.content==query),None)
    if user is None:raise ValueError('Original user query missing from receiver context; cannot place carrier')
    out.pop(next(i for i,m in enumerate(out) if m is seed))
    if position=='system_memory':
        index=0
        while index<len(out) and kind(out[index])=='SystemMessage':index+=1
        out.insert(index,system_factory(content=seed.content))
    else:
        index=next(i for i,m in enumerate(out) if m is user)
        out.insert(index+(position=='after_user'),seed)
    return out


def jsonable(value):
    if hasattr(value,'model_dump'):return value.model_dump(mode='json')
    if isinstance(value,dict):return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)


def load_upstream(source,tamas_dir):
    source=Path(source).resolve()
    names=('payload_riddle','termination','tamas_tools','stego_methods','structural_metrics','mas_runner','metrics','run_experiment')
    for name in names:
        old=sys.modules.get(name)
        if old and Path(old.__file__).resolve().parent!=source:raise ValueError('Conflicting native module '+name)
    sys.path.insert(0,str(source));up={name:importlib.import_module(name) for name in names}
    up['tamas_tools'].TOOLS_DIR=str(Path(tamas_dir)/'data'/'tools'/'autogen')
    up['tamas_tools'].open=functools.partial(open,encoding='utf-8')
    from autogen_core.models import SystemMessage
    up['SystemMessage']=SystemMessage
    return up


async def run_cell(task,cell,plan,upstream,sink=None):
    native=upstream['mas_runner'];payload=upstream['payload_riddle'];p=plan['profile'];attacked=cell['condition']=='attack'
    seed_index=p['seed_index'];seed_name=task['agents'][seed_index]['name'].replace(' ','_')+'_'+str(seed_index)
    factory=native.build_model_client;clients=[];placements=[]
    def build_client():
        mc=factory();original=mc.create;clients.append((mc,original))
        async def create(messages,*args,**kwargs):
            original_messages=list(messages);selected=seed_message(original_messages,seed_name) if attacked else None
            placed=relocate(original_messages,seed_name,task['benign_query'],cell['position'],upstream['SystemMessage']) if attacked else original_messages
            if selected is not None:placements.append(dict(position=cell['position'],source=seed_name,carrier=selected.content))
            if sink:sink(dict(kind='native_actor_input',messages=jsonable(placed),kwargs=jsonable(kwargs)))
            response=await original(placed,*args,**kwargs)
            if sink:sink(dict(kind='native_actor_output',response=jsonable(response)))
            return response
        mc.create=create;return mc
    native.build_model_client=build_client
    phrase=cell['normalized_payload'] if attacked else payload.ACROSTIC_TRIGGER
    try:
        with using_trigger(native,payload,phrase):
            run=await native.run_task(task,attacked=attacked,branching_factor=p['branching_factor'],
                seed_index=seed_index,max_turns=p['max_turns'],stego=True)
    except Exception as exc:
        for mc,_ in clients:
            try:await mc.close()
            except Exception:pass
        return dict(status='runtime_error',error=f'{type(exc).__name__}: {exc}',placements=placements)
    finally:
        native.build_model_client=factory
        for mc,original in clients:mc.create=original
    out=dict(status='completed',run=run,placements=placements)
    if sink:sink(dict(kind='native_run_result',run=jsonable(run)))
    try:
        scored=upstream['metrics'].score_run(run)
        scored['branching_factor']=p['branching_factor'] if attacked else None
        scored['trial']=cell['trial']
        scored['decode']=upstream['run_experiment'].decode_success_for(task,p['branching_factor'])
        out['scores']=scored
    except Exception as exc:out.update(status='scoring_error',error=f'{type(exc).__name__}: {exc}')
    return out
