"""Versioned operations sessions; native experiment and audit semantics stay frozen."""
import hashlib
import json
import os
from pathlib import Path
import re

from experiments.acrostic_ablation.storage import RunStore, exclusive_lock, save

ACKNOWLEDGED_KEY='9e26e7176ccc820d55761adf'
SECOND_KEY='88699a66c4c865a3cc78c8d0'
THIRD_KEY='a6def086abf1b1b0f74b46ef'
RESUME_PROFILES={
    'resume-20261027':dict(started=344,pending=536,keys={ACKNOWLEDGED_KEY},
        previous='parallel',instruction='那你继续跑吧？'),
    'resume-20261027-b':dict(started=467,pending=413,keys={ACKNOWLEDGED_KEY,SECOND_KEY},
        previous='parallel/sessions/resume-20261027',instruction='继续'),
    'resume-20261027-c':dict(started=499,pending=381,keys={ACKNOWLEDGED_KEY,SECOND_KEY,THIRD_KEY},
        previous='parallel/sessions/resume-20261027-b',instruction='继续啊'),
    'resume-20261027-unattended':dict(continue_on_error=True,minimum_started=499,
        previous='parallel/sessions/resume-20261027-c',
        instruction='失败了也继续跑；不用监控，明天用户再询问结果'),
}
CONTINUABLE_ERRORS={'runtime_error','scoring_error'}


def resume_profile():
    try:return RESUME_PROFILES[os.environ.get('SCB_FIXED_SESSION','')]
    except KeyError:raise ValueError('No explicit user authorization for this continuation session')


def validate_resume_inventory(store,profile):
    rows=store.records();errors=[r for r in rows if r['status']!='completed']
    if profile.get('continue_on_error'):
        if len(rows)<profile['minimum_started'] or any(r['status'] not in CONTINUABLE_ERRORS for r in errors):
            raise ValueError('Unattended continuation requires intact terminal evidence; unknown/evidence errors block')
        return
    if (len(rows)!=profile['started'] or len(store.unstarted())!=profile['pending']
        or len(errors)!=len(profile['keys']) or {r['key'] for r in errors}!=profile['keys']
        or any(r['status']!='runtime_error' for r in errors)):
        raise ValueError('Inventory differs from the exact user-authorized continuation scope')


def management_dir(root):
    name=os.environ.get('SCB_FIXED_SESSION','')
    if name and not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',name):
        raise ValueError('Invalid operations session name')
    path=Path(root)/'parallel'
    return path/'sessions'/name if name else path


def acknowledged_failures(store):
    if not os.environ.get('SCB_FIXED_SESSION'):return {}
    path=management_dir(store.root)/'authorization.json'
    raw=path.read_bytes()
    expected=os.environ.get('SCB_FIXED_AUTH_SHA')
    if expected and hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Session authorization changed')
    value=json.loads(raw)
    if value['plan_sha256']!=store.plan['plan_sha256']:raise ValueError('Acknowledgment plan differs')
    accepted=value['acknowledged_failures']
    unattended=authorized_error_policy(value)
    if not unattended and len(accepted) not in (1,2,3):raise ValueError('Only the explicitly investigated one, two or three failures may be acknowledged')
    for key,wanted in accepted.items():
        if key not in store.cells:raise ValueError('Acknowledged key is outside the frozen plan')
        path=store.root/'attempts'/key/'result.json'
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=wanted:
            raise ValueError('Acknowledged failure bytes changed')
        row=json.loads(path.read_bytes())
        if row.get('key')!=key or row.get('status') not in (CONTINUABLE_ERRORS if unattended else {'runtime_error'}):
            raise ValueError('Only an immutable terminal runtime failure can be acknowledged')
    return accepted


def authorized_error_policy(authorization):
    return (os.environ.get('SCB_FIXED_SESSION')=='resume-20261027-unattended'
        and authorization.get('continue_on_error') is True)


def continue_on_error(store):
    if os.environ.get('SCB_FIXED_SESSION')!='resume-20261027-unattended':return False
    raw=(management_dir(store.root)/'authorization.json').read_bytes()
    expected=os.environ.get('SCB_FIXED_AUTH_SHA')
    if expected and hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Session authorization changed')
    value=json.loads(raw)
    if value['plan_sha256']!=store.plan['plan_sha256']:raise ValueError('Error policy plan differs')
    return authorized_error_policy(value)


def recorded_error_issues(store):
    return sorted(r['key']+': '+r['status'] for r in store.records() if r['status'] in CONTINUABLE_ERRORS)


def allowed_issues(accepted):
    return sorted(key+': runtime_error' for key in accepted)


def coverage_audit(store,native_audit):
    accepted=acknowledged_failures(store);rows=store.records()
    counts={status:sum(r['status']==status for r in rows) for status in {r['status'] for r in rows}}
    if continue_on_error(store):
        ok=(len(rows)==len(store.cells) and all(r['status'] in CONTINUABLE_ERRORS|{'completed'} for r in rows)
            and sorted(native_audit['issues'])==recorded_error_issues(store))
        return dict(ok=ok,planned=len(store.cells),terminal=len(rows),statuses=counts,continue_on_error=True,
            acknowledged_failures=accepted,native_audit_ok=native_audit['ok'],native_audit_issues=native_audit['issues'],
            human_review='pending',interpretation='All planned attempts terminal; genuine runtime/scoring errors retained, not all successful')
    ok=(len(rows)==len(store.cells) and counts.get('completed',0)==len(store.cells)-len(accepted)
        and counts.get('runtime_error',0)==len(accepted)
        and sorted(native_audit['issues'])==allowed_issues(accepted))
    return dict(ok=ok,planned=len(store.cells),terminal=len(rows),statuses=counts,
        acknowledged_failures=accepted,native_audit_ok=native_audit['ok'],
        native_audit_issues=native_audit['issues'],human_review='pending',
        interpretation=f'Coverage with {len(accepted)} preserved genuine runtime failures; not all runs completed successfully')


def require_resume_continuation(plan,root):
    from experiments.fixed_carrier_study.cli import audit
    from ops.fixed_study_parallel import require_preserved, validate_inventory
    store=RunStore(root,plan);value=json.loads((management_dir(root)/'authorization.json').read_bytes())
    accepted=acknowledged_failures(store)
    profile=resume_profile()
    expected={r['key'] for r in store.records() if r['status'] in CONTINUABLE_ERRORS} if profile.get('continue_on_error') else profile['keys']
    if set(accepted)!=expected:raise ValueError('Acknowledged failures differ from this exact authorization')
    validate_resume_inventory(store,profile)
    require_preserved(root,value['before_sha256']);validate_inventory(store)
    partial=audit(plan,root,'all',allow_unstarted=True);pilot=audit(plan,root,'pilot')
    expected_issues=recorded_error_issues(store) if profile.get('continue_on_error') else allowed_issues(accepted)
    if sorted(partial['issues'])!=expected_issues or not pilot['ok']:
        raise ValueError('Resume requires intact native evidence and successful original pilot: '+str(partial['issues'][:5]))
    save(management_dir(root)/'preflight-native-partial-audit.json',partial)
    save(management_dir(root)/'preflight-native-pilot-audit.json',pilot)


def seal_resume(args):
    from ops.fixed_study_parallel import read_plan, snapshot, require_preserved, validate_inventory, process_birth
    from experiments.fixed_carrier_study.cli import audit,verify_files
    root=args.output.resolve();session=management_dir(root)
    if session==root/'parallel':raise ValueError('A new named operations session is required')
    with exclusive_lock(root/'run.lock'):
        plan=read_plan(root);verify_files(plan,args.source_repo,args.tamas_dir,root)
        store=RunStore(root,plan);validate_inventory(store)
        profile=resume_profile();prior=root/profile['previous']
        previous=json.loads((prior/'controller-result.json').read_bytes())
        if previous['cleanup_errors']:raise ValueError('Previous cleanup unresolved')
        pids=json.loads((prior/'worker-pids.json').read_bytes())
        leader=json.loads((prior/'controller.pid.json').read_bytes())['pid']
        if any(process_birth(pid) is not None for pid in [leader]+pids['workers']+pids['servers']):
            raise ValueError('Previous managed PID still exists; inspect identity before continuation')
        validate_resume_inventory(store,profile)
        error_keys={r['key'] for r in store.records() if r['status'] in CONTINUABLE_ERRORS} if profile.get('continue_on_error') else profile['keys']
        if profile['previous']!='parallel':
            previous_authorization=json.loads((prior/'authorization.json').read_bytes())
            require_preserved(root,previous_authorization['before_sha256'])
        native=audit(plan,root,'all',allow_unstarted=True)
        expected_issues=recorded_error_issues(store) if profile.get('continue_on_error') else allowed_issues(error_keys)
        if sorted(native['issues'])!=expected_issues or not audit(plan,root,'pilot')['ok']:
            raise ValueError('Unexpected native evidence issue before sealing')
        require_preserved(root,json.loads((root/'parallel/pre-transition-sha256.json').read_bytes()))
        session.mkdir(parents=True,exist_ok=False)
        authorization=dict(plan_sha256=plan['plan_sha256'],
            acknowledged_failures={key:hashlib.sha256((root/'attempts'/key/'result.json').read_bytes()).hexdigest()
                for key in sorted(error_keys)},
            before_sha256=snapshot(root),previous_controller_result=previous,
            previous_session=profile['previous'],user_instruction=profile['instruction'],
            scope=f"Only {len(store.unstarted())} never-started cells; same frozen runtime; retain all failures",
            continue_on_error=profile.get('continue_on_error',False))
        with (session/'authorization.json').open('x',encoding='utf-8') as stream:
            json.dump(authorization,stream,ensure_ascii=False,indent=2)
        save(session/'sealed-native-partial-audit.json',native)
        print(json.dumps(dict(sealed=True,session=str(session),completed=sum(r['status']=='completed' for r in store.records()),
            preserved_errors=len(error_keys),unstarted=len(store.unstarted()),continue_on_error=profile.get('continue_on_error',False))))
