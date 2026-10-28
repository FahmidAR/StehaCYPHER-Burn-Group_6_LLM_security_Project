"""Fixed880manifest; pilot20 and continuation share keys and all native score fields."""
import argparse
import asyncio
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from experiments.acrostic_ablation.baseline import source_snapshot,tree_hashes,load_tasks
from experiments.acrostic_ablation.cli import preflight,configure_environment
from experiments.acrostic_ablation.design import digest
from experiments.acrostic_ablation.report import write_report,summarize
from experiments.acrostic_ablation.storage import RunStore,execute_pending,exclusive_lock,freeze_plan,require_approval,save,sign_plan
from .study import SCHEMA,EXPECTED_TASK_SHA,build_plan,phase_keys
from .evidence import check_events


def extension_hashes():
    root=Path(__file__).resolve().parents[1]
    paths=list((root/'fixed_carrier_study').glob('*.py'))+list((root/'acrostic_ablation').glob('*.py'))
    paths+=[root/'task_stego/generator.py',root/'task_stego/ranged.py']
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in sorted(paths)}


def verify_design(plan):
    if plan.get('schema')!=SCHEMA or len(plan.get('tasks',[]))!=88 or digest(plan['tasks'])!=EXPECTED_TASK_SHA:
        raise ValueError('Exact original88task identity/schema required')
    expected=build_plan(plan['tasks'])
    for key,value in expected.items():
        if plan.get(key)!=value:raise ValueError('Frozen protocol differs: '+key)


def prepare(repo,tamas_dir,output,base_url):
    source,source_hashes=source_snapshot(repo,Path(output)/'baseline-source')
    tasks=load_tasks(source,tamas_dir,88);plan=build_plan(tasks);verify_design(plan)
    data_hashes=tree_hashes(Path(tamas_dir)/'data')
    if not data_hashes:raise ValueError('Original TAMAS snapshot required')
    plan.update(source_sha256=source_hashes,data_sha256=data_hashes,extension_sha256=extension_hashes(),
        model_base_url=base_url,dataset_origin='original teammate benign loader and frozen same88task list',
        scoring_revision='unmodified native score_run and GO codec control')
    plan=sign_plan(plan);freeze_plan(output,plan)
    write_report(output,plan,RunStore(output,plan).records());return plan


def verify_files(plan,repo,tamas_dir,output):
    require_approval(plan,plan.get('plan_sha256'));verify_design(plan)
    source,hashes=source_snapshot(repo,Path(output)/'baseline-source')
    if hashes!=plan['source_sha256']:raise ValueError('Original source differs')
    if extension_hashes()!=plan['extension_sha256']:raise ValueError('Extension code differs from frozen plan')
    if tree_hashes(Path(tamas_dir)/'data')!=plan['data_sha256']:raise ValueError('Dataset differs from frozen plan')
    return source


def audit(plan,root,phase,allow_unstarted=False):
    root=Path(root);store=RunStore(root,plan);records=store.records();lookup={r['key']:r for r in records}
    selected=phase_keys(plan,phase);cells={c['key']:c for c in plan['cells']};issues=[]
    tasks={t['task_id']:t for t in plan['tasks']}
    required_fields={'task_id','task_completion','p_asr','ptn','ers','token_usage','completion_time_turns','stealth_sim','completion_combined','decode'}
    for key in selected:
        row=lookup.get(key);cell=cells[key]
        if row is None:
            if not allow_unstarted:issues.append(key+': unstarted')
            continue
        if row['status']!='completed':issues.append(key+': '+row['status']);continue
        diag=row.get('diagnostics',{})
        if diag.get('transport_errors'):issues.append(key+': native API transport errors')
        if diag.get('human_review')!='pending':issues.append(key+': unexpected human review state')
        if not required_fields<=set(row.get('scores',{})):issues.append(key+': missing native score fields')
        if row.get('scores',{}).get('task_id')!=cell['task_id']:issues.append(key+': score task mismatch')
        folder=store.folder(cell)
        try:events=[json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines() if line]
        except (OSError,ValueError) as exc:issues.append(key+': event journal invalid '+str(exc));continue
        if not events:issues.append(key+': no events')
        issues.extend(key+': '+issue for issue in check_events(tasks[cell['task_id']],cell,row,events))
        if any(e['kind'] in ('native_actor_error','native_judge_error') for e in events):issues.append(key+': API error event')
        injected=[e for e in events if e['kind']=='fixed_attacker_stimulus']
        if cell['condition']=='attack':
            if len(injected)!=1 or diag.get('seed_bypasses')!=1:issues.append(key+': wrong stimulus count')
            elif (injected[0].get('model_generated') is not False or injected[0].get('text')!=cell['carrier']['text']):issues.append(key+': changed/mislabeled stimulus')
            transcript=row.get('run',{}).get('transcript',[])
            if not transcript or transcript[0][1]!=cell['carrier']['text']:issues.append(key+': transcript stimulus mismatch')
            for placed in row.get('placements',[]):
                if placed.get('carrier')!=cell['carrier']['text'] or placed.get('position')!=cell['position']:issues.append(key+': carrier placement mismatch')
        elif injected or diag.get('seed_bypasses')!=0:issues.append(key+': clean stimulus contamination')
    expected=summarize(plan,records)
    try:
        if json.loads((root/'summary.json').read_text(encoding='utf-8'))!=expected:issues.append('summary differs from all recorded native scores')
        with (root/'matrix.csv').open(encoding='utf-8',newline='') as f:matrix=list(csv.DictReader(f))
        if len(matrix)!=880 or {r['ablation_key'] for r in matrix}!=set(cells):issues.append('matrix must keep exact880unique planned rows')
        for row in matrix:
            recorded=lookup.get(row['ablation_key'],{})
            if row['ablation_status']!=recorded.get('status','unstarted'):issues.append('CSV status mismatch '+row['ablation_key'])
            for field,value in recorded.get('scores',{}).items():
                wanted=json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else ('' if value is None else str(value))
                if row.get(field)!=wanted:issues.append('CSV score mismatch '+row['ablation_key']+':'+field)
    except (OSError,ValueError,KeyError) as exc:issues.append('export invalid: '+str(exc))
    return dict(ok=not issues,phase=phase,required=len(selected),started=sum(k in lookup for k in selected),
        formal_tasks=88,formal_planned=880,total_started=len(records),allow_unstarted=allow_unstarted,issues=issues,human_review='pending')


def require_continuation(plan,root,phase):
    phase_keys(plan,phase)
    existing=audit(plan,root,'all',allow_unstarted=True)
    if not existing['ok']:raise ValueError('Existing failed/interrupted/invalid evidence requires investigation before another key: '+str(existing['issues'][:5]))
    if phase=='all':
        pilot=audit(plan,root,'pilot')
        if not pilot['ok']:raise ValueError('Successful fresh20-cell pilot audit required before formal continuation')


def execute(plan,approved_sha,repo,tamas_dir,output,phase):
    require_approval(plan,approved_sha)
    with exclusive_lock(Path(output)/'run.lock'):
        source=verify_files(plan,repo,tamas_dir,output)
        require_continuation(plan,output,phase)
        fingerprint=preflight(plan)
        if fingerprint['ollama_models']['qwen3.5:35b']['digest']!='72aac7c28be8ff9b81c2a270eb489c88e6d822a76ec0cb7bf34d965768848567':
            raise ValueError('Original actor weight digest differs')
        runtime=Path(output)/'runtime.json'
        if runtime.exists() and json.loads(runtime.read_text(encoding='utf-8'))!=fingerprint:raise ValueError('Runtime/model identity differs; no mixed batch')
        save(runtime,fingerprint);configure_environment(plan)
        from autogen_core.models import CreateResult,RequestUsage
        from experiments.acrostic_ablation.runner import load_upstream
        from .runner import run_cell
        upstream=load_upstream(source,tamas_dir)
        upstream['fixed_result']=lambda text:CreateResult(content=text,finish_reason='stop',
            usage=RequestUsage(prompt_tokens=0,completion_tokens=0),cached=False)
        store=RunStore(output,plan)
        async def one(task,cell,approved_plan):
            with (store.folder(cell)/'events.jsonl').open('x',encoding='utf-8') as stream:
                def sink(record):stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                result=await run_cell(task,cell,approved_plan,upstream,sink)
            if result['diagnostics']['transport_errors']:
                result.update(status='runtime_error',error='Native transport error; raw scores retained but not treated as valid judging')
            return result
        try:asyncio.run(execute_pending({**plan,'execution_order':phase_keys(plan,phase)},store,one))
        finally:write_report(output,plan,store.records())
        checked=audit(plan,output,phase);save(Path(output)/('audit-'+phase+'.json'),checked);return checked


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['prepare','pilot','all','audit-pilot','audit-all'],default='prepare')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tamas-dir',type=Path,required=True)
    parser.add_argument('--source-repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--base-url',default='http://127.0.0.1:11435/v1');parser.add_argument('--approved-plan-sha')
    args=parser.parse_args(argv)
    try:
        if args.phase=='prepare':
            plan=prepare(args.source_repo,args.tamas_dir,args.output,args.base_url)
            print(json.dumps(dict(mode='PREPARED ONLY',tasks=88,planned=880,pilot=20,plan_sha256=plan['plan_sha256']),indent=2));return 0
        plan=json.loads((args.output/'plan.json').read_text(encoding='utf-8'))
        if args.phase.startswith('audit-'):
            verify_files(plan,args.source_repo,args.tamas_dir,args.output);result=audit(plan,args.output,args.phase[6:])
            save(args.output/(args.phase+'.json'),result)
        else:result=execute(plan,args.approved_plan_sha,args.source_repo,args.tamas_dir,args.output,args.phase)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['ok'] else 1
    except (ValueError,FileNotFoundError) as exc:print(str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
