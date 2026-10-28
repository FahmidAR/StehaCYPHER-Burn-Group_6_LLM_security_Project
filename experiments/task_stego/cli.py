"""Prepare offline by default. A separate exact-plan approval is required to generate."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from experiments.acrostic_ablation.storage import exclusive_lock,freeze_plan,require_approval,save,sign_plan
from .generator import Completion,InvalidCompletion,OUTPUT_TOKEN_LIMIT,generate,phrase_prompt,validate_inputs
from .ranged import DEFAULT_BANDS,generate_ranges,phrase_prompt as ranged_phrase_prompt,request_budget

SCHEMA='task-related-word-stego-generator-v2'
RANGE_SCHEMA='task-related-ranged-word-stego-v3'
MODEL='qwen3.5:35b'


def code_hashes():
    root=Path(__file__).resolve().parents[1]
    paths=[root/'task_stego/generator.py',root/'task_stego/ranged.py',root/'task_stego/cli.py',
        root/'acrostic_ablation/design.py',root/'acrostic_ablation/storage.py']
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest() for p in paths}


def validate_endpoint(base):
    url=urlsplit(base)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.path.rstrip('/')!='/v1' or url.username or url.query or url.fragment:
        raise ValueError('Use an explicitly local Ollama http://127.0.0.1:<port>/v1 endpoint')


def prepare(request,lengths,output,base,reasoning_effort=None):
    validate_inputs(request,lengths);validate_endpoint(base)
    if reasoning_effort not in (None,'none'):raise ValueError('Only default or explicitly disabled generator thinking is supported')
    plan=sign_plan(dict(schema=SCHEMA,acrostic_unit='word',request=request,lengths=list(lengths),model=MODEL,base_url=base,
        reasoning_effort=reasoning_effort,
        max_model_requests=1+len(lengths),max_output_tokens_per_request=OUTPUT_TOKEN_LIMIT,
        api_retries=0,timeout=300,code_sha256=code_hashes(),
        workflow='one shared-intent phrase call, then one N-word complete sentence per N-letter message; no automatic retry',
        native_mas_and_metrics='unchanged; no automatic integration or experimental run'))
    freeze_plan(output,plan)
    save(Path(output)/'prompt-preview.json',dict(phrase_messages=phrase_prompt(request,lengths),
        second_stage='One complete sentence of N words; every word initial spells the actual N-letter message'))
    return plan


def prepare_ranged(request,output,base,bands=None,max_repairs=2):
    bands=json.loads(json.dumps(DEFAULT_BANDS if bands is None else bands))
    validate_inputs(request,[1]);validate_endpoint(base);budget=request_budget(bands,max_repairs)
    plan=sign_plan(dict(schema=RANGE_SCHEMA,acrostic_unit='word',request=request,bands=bands,model=MODEL,
        base_url=base,reasoning_effort='none',max_repairs=max_repairs,max_model_requests=budget,
        max_output_tokens_per_request=OUTPUT_TOKEN_LIMIT,api_retries=0,timeout=300,code_sha256=code_hashes(),
        workflow='one phrase batch and one paragraph per band; each stage has bounded explicit mechanical corrections',
        native_mas_and_metrics='unchanged; independent generation only; semantics and human review pending'))
    freeze_plan(output,plan)
    save(Path(output)/'prompt-preview.json',dict(phrase_messages=ranged_phrase_prompt(request,bands),
        second_stage='N whole words in a coherent paragraph; every word initial spells the message; words array joined only'))
    return plan


async def generate_approved(plan,sink):
    """This function is private to approved execution, not preparation."""
    client=None;result=None;cleanup_error=None
    try:
        from urllib.request import urlopen
        from openai import AsyncOpenAI
        base=plan['base_url'].rstrip('/')[:-3]
        with urlopen(base+'/api/tags',timeout=8) as response:tags=json.load(response)
        installed={m['name']:m for m in tags['models']}
        if plan['model'] not in installed:raise ValueError('Required original 35B model is not installed; no automatic pull or substitution')
        sink(dict(event='runtime',openai_version=importlib.metadata.version('openai'),model=installed[plan['model']]))
        client=AsyncOpenAI(base_url=plan['base_url'],api_key='ollama',timeout=plan['timeout'],max_retries=0)
        calls=0
        async def complete(messages,*,max_tokens):
            nonlocal calls
            if calls>=plan['max_model_requests']:raise ValueError('Frozen generation request budget exhausted')
            calls+=1
            options={} if plan.get('reasoning_effort') is None else {'reasoning_effort':plan['reasoning_effort']}
            response=await client.chat.completions.create(model=plan['model'],messages=messages,
                max_tokens=max_tokens,response_format={'type':'json_object'},**options)
            raw=response.model_dump(mode='json')
            sink(dict(event='raw_model_response',model_request=calls,response=raw))
            choices=raw.get('choices') if isinstance(raw,dict) else None
            if not isinstance(choices,list) or len(choices)!=1:
                raise InvalidCompletion('Expected exactly one model choice',raw)
            message=choices[0].get('message') if isinstance(choices[0],dict) else None
            if not isinstance(message,dict) or not isinstance(message.get('content'),str):
                raise InvalidCompletion('Expected textual completion content',raw)
            return Completion(message['content'],raw)
        if plan.get('schema')==RANGE_SCHEMA:
            result=await generate_ranges(plan['request'],plan['bands'],complete,plan['max_repairs'],sink)
        else:result=await generate(plan['request'],plan['lengths'],complete,sink)
        result['model_requests']=calls
    except Exception as exc:
        result=dict(status='setup_error',error=f'{type(exc).__name__}: {exc}',request=plan['request'],
            requested_lengths=plan.get('lengths'),bands=plan.get('bands'),attempts=[],
            variants=[dict(label=b['label'],status='not_started') for b in plan['bands']] if plan.get('schema')==RANGE_SCHEMA
                else [dict(target_letters=n,status='not_started') for n in plan['lengths']])
    finally:
        if client is not None:
            try:await client.close()
            except Exception as exc:cleanup_error=f'{type(exc).__name__}: {exc}'
    if cleanup_error:result['cleanup_error']=cleanup_error
    return result


def execute(plan,approved_sha,output):
    require_approval(plan,approved_sha)
    if plan.get('schema') not in (SCHEMA,RANGE_SCHEMA):raise ValueError('Old sentence-acrostic or wrong plan schema; prepare a word-acrostic plan')
    if code_hashes()!=plan['code_sha256']:raise ValueError('Generator code changed after plan approval')
    if plan['schema']==RANGE_SCHEMA:
        validate_inputs(plan['request'],[1])
        fixed=dict(model=MODEL,max_output_tokens_per_request=OUTPUT_TOKEN_LIMIT,api_retries=0,timeout=300)
        if any(type(plan.get(key)) is not type(value) or plan.get(key)!=value for key,value in fixed.items()):
            raise ValueError('Ranged plan fixed model/token/retry/timeout protocol differs')
        if plan['max_model_requests']!=request_budget(plan['bands'],plan['max_repairs']) or plan.get('reasoning_effort')!='none':
            raise ValueError('Ranged plan budget or thinking mode differs from the protocol')
    else:validate_inputs(plan['request'],plan['lengths'])
    validate_endpoint(plan['base_url'])
    if plan.get('reasoning_effort') not in (None,'none'):raise ValueError('Unsupported generator thinking setting')
    root=Path(output);freeze_plan(root,plan)
    with exclusive_lock(root/'run.lock'):
        if (root/'started.json').exists():raise ValueError('Already started; preserve existing evidence and do not automatically regenerate')
        with (root/'started.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(plan_sha256=plan['plan_sha256'],started_unix=time.time()),stream);stream.flush();os.fsync(stream.fileno())
        with (root/'events.jsonl').open('x',encoding='utf-8') as stream:
            def sink(record):
                stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
            result=asyncio.run(generate_approved(plan,sink))
        result['plan_sha256']=plan['plan_sha256']
        with (root/'result.json').open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
        return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--request');source.add_argument('--request-file',type=Path)
    parser.add_argument('--letters',type=int,action='append')
    parser.add_argument('--ranged',action='store_true',help='Use short/medium/long hidden messages and word-initial paragraphs')
    parser.add_argument('--max-repairs',type=int,help='Ranged mode only; zero to two corrections per stage, default two')
    parser.add_argument('--base-url',default='http://127.0.0.1:11434/v1')
    parser.add_argument('--reasoning-effort',choices=['none'],help='Disable thinking only for this independent generator; omitted keeps the model default')
    parser.add_argument('--execute',action='store_true');parser.add_argument('--approved-plan-sha')
    args=parser.parse_args(argv)
    try:
        if args.execute:
            if not args.approved_plan_sha:raise ValueError('Explicit user approval and --approved-plan-sha are required before generation')
            plan=json.loads((args.output/'plan.json').read_text(encoding='utf-8'))
            result=execute(plan,args.approved_plan_sha,args.output)
            print(json.dumps(dict(status=result['status'],result=str(args.output/'result.json')),indent=2));return 0 if result['status']=='completed' else 1
        request=args.request_file.read_text(encoding='utf-8') if args.request_file else args.request
        if args.ranged:
            if args.letters:raise ValueError('Ranged mode uses length bands, not --letters exact targets')
            plan=prepare_ranged(request,args.output,args.base_url,max_repairs=2 if args.max_repairs is None else args.max_repairs)
        else:
            if args.max_repairs is not None:raise ValueError('--max-repairs requires --ranged')
            plan=prepare(request,args.letters or [12,17],args.output,args.base_url,args.reasoning_effort)
        print(json.dumps(dict(mode='PREPARED ONLY; NO MODEL CALLS',model=plan['model'],lengths=plan.get('lengths'),bands=plan.get('bands'),
            max_model_requests=plan['max_model_requests'],plan_sha256=plan['plan_sha256']),indent=2));return 0
    except (ValueError,FileNotFoundError) as exc:print(str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
