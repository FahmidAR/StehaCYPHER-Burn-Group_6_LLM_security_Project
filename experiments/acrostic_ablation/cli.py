"""Default is offline preparation; execution requires explicit frozen-plan approval."""
import argparse
import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from .baseline import extension_hashes,load_tasks,source_snapshot,tree_hashes
from .design import DEFAULT_PAYLOADS,SCHEMA,build_plan
from .report import write_report
from .storage import RunStore,execute_pending,exclusive_lock,freeze_plan,require_approval,save,sign_plan


def prepare(repo,tamas_dir,output,payloads,num_tasks,trials,base_url):
    source,hashes=source_snapshot(repo,Path(output)/'baseline-source')
    data_hashes=tree_hashes(Path(tamas_dir)/'data')
    if not data_hashes:raise ValueError('Original TAMAS data tree required')
    tasks=load_tasks(source,tamas_dir,num_tasks)
    plan=build_plan(tasks,payloads,trials)
    plan.update(source_sha256=hashes,data_sha256=data_hashes,extension_sha256=extension_hashes(),
        model_base_url=base_url,dataset_origin='TAMAS snapshot; upstream benign extraction; data hash manifest',
        scoring_revision='unmodified teammate score_run and decode_success_for')
    plan=sign_plan(plan);freeze_plan(output,plan)
    write_report(output,plan,RunStore(output,plan).records())
    return plan


def verify_files(plan,repo,tamas_dir,output):
    require_native_plan(plan)
    source,hashes=source_snapshot(repo,Path(output)/'baseline-source')
    if hashes!=plan['source_sha256']:raise ValueError('Pinned source hashes differ')
    if extension_hashes()!=plan['extension_sha256']:raise ValueError('Extension code differs from approved plan')
    if tree_hashes(Path(tamas_dir)/'data')!=plan['data_sha256']:raise ValueError('Dataset differs from approved plan')
    return source


def require_native_plan(plan):
    if plan.get('schema')!=SCHEMA:raise ValueError('Superseded template/extra-judge plan: prepare the corrected native plan; do not execute this one')


def preflight(plan):
    """Metadata only, called ONLY after approval. Never start/pull/replace models."""
    from urllib.request import urlopen
    base=plan['model_base_url'];url=urlsplit(base)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.path.rstrip('/')!='/v1' or url.username or url.query:
        raise ValueError('Only a local Ollama /v1 endpoint is supported; no paid/external API fallback')
    versions={name:importlib.metadata.version(name) for name in ('autogen-agentchat','autogen-ext','autogen-core','openai')}
    server=base.rstrip('/')[:-3]
    with urlopen(server+'/api/tags',timeout=8) as response:tags=json.load(response)
    models={m['name']:m for m in tags['models']}
    required=[plan['profile']['model'],plan['profile']['judge_model']]
    if any(name not in models for name in required):raise ValueError('Required teammate Ollama models are not installed; no automatic pull/substitution')
    return dict(packages=versions,ollama_models={name:models[name] for name in required},endpoint=base)


def configure_environment(plan):
    p=plan['profile']
    for key,value in dict(MODEL_NAME=p['model'],JUDGE_MODEL=p['judge_model'],MODEL_BASE_URL=plan['model_base_url'],
        MODEL_API_KEY='ollama',AGENT_TIMEOUT=p['agent_timeout'],AGENT_MAX_RETRIES=p['agent_max_retries'],
        JUDGE_TIMEOUT=p['judge_timeout'],MAX_TURNS=p['max_turns']).items():os.environ[key]=str(value)
    os.environ.pop('MODEL_TEMPERATURE',None)  # teammate launcher leaves temperature unset


def execute(plan,approved_sha,repo,tamas_dir,output):
    require_approval(plan,approved_sha)  # before optional framework imports or ANY network
    with exclusive_lock(Path(output)/'run.lock'):
        source=verify_files(plan,repo,tamas_dir,output)
        fingerprint=preflight(plan)
        existing=Path(output)/'runtime.json'
        if existing.exists() and json.loads(existing.read_text(encoding='utf-8'))!=fingerprint:
            raise ValueError('Runtime/model digest changed; do not mix versions in this matrix')
        save(existing,fingerprint)
        configure_environment(plan)
        from .runner import load_upstream,run_cell
        upstream=load_upstream(source,tamas_dir)
        store=RunStore(output,plan)
        async def one(task,cell,approved_plan):
            folder=store.folder(cell)
            with (folder/'events.jsonl').open('x',encoding='utf-8') as stream:
                def sink(record):
                    stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                return await run_cell(task,cell,approved_plan,upstream,sink)
        try:asyncio.run(execute_pending(plan,store,one))
        finally:summary=write_report(output,plan,store.records())
        return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--tamas-dir',type=Path)
    parser.add_argument('--payload',action='append')
    parser.add_argument('--num-tasks',type=int,default=88)
    parser.add_argument('--trials',type=int,default=1)
    parser.add_argument('--base-url',default='http://127.0.0.1:11434/v1')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--approved-plan-sha')
    parser.add_argument('--summarize-only',action='store_true')
    args=parser.parse_args(argv);repo=Path(__file__).resolve().parents[2]
    try:
        if args.execute and not args.approved_plan_sha:raise ValueError('Execution requires explicit user approval and --approved-plan-sha')
        if args.execute and args.summarize_only:raise ValueError('Choose execution or offline summary')
        if args.execute or args.summarize_only:
            plan=json.loads((args.output/'plan.json').read_text(encoding='utf-8'))
            require_approval(plan,plan['plan_sha256'])
            require_native_plan(plan)
            if args.execute:
                if args.tamas_dir is None:raise ValueError('--tamas-dir is required')
                summary=execute(plan,args.approved_plan_sha,repo,args.tamas_dir,args.output)
            else:summary=write_report(args.output,plan,RunStore(args.output,plan).records())
            print(json.dumps(dict(planned=summary['planned'],started=summary['started']),indent=2));return 0
        if args.tamas_dir is None:raise ValueError('--tamas-dir is required for offline preparation')
        plan=prepare(repo,args.tamas_dir,args.output,args.payload or DEFAULT_PAYLOADS,args.num_tasks,args.trials,args.base_url)
        print(json.dumps(dict(mode='PREPARED ONLY; NOT RUN',planned=len(plan['cells']),profile=plan['profile'],
            plan_sha256=plan['plan_sha256']),indent=2));return 0
    except (ValueError,FileNotFoundError) as exc:
        print(str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
