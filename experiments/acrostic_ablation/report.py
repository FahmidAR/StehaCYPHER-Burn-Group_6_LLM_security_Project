"""Original score fields verbatim, grouped by the two requested variables."""
import csv
import json
from pathlib import Path
import statistics
from .storage import save


def summarize(plan,records):
    by_key={r['key']:r for r in records}
    if len(by_key)!=len(records) or not set(by_key).issubset({c['key'] for c in plan['cells']}):raise ValueError('Duplicate/foreign run keys')
    groups={}
    for c in plan['cells']:groups.setdefault((c['condition'],c['payload'],c['position']),[]).append(c)
    output=[]
    for (condition,payload,position),cells in groups.items():
        rows=[by_key.get(c['key'],{}) for c in cells];scores=[r['scores'] for r in rows if 'scores' in r]
        keys=sorted(set().union(*(s.keys() for s in scores))) if scores else []
        means={};counts={}
        for key in keys:
            values=[s[key] for s in scores if type(s.get(key)) in (int,float,bool)]
            if values:means[key]=round(statistics.mean(values),2 if key=='task_completion' else 3);counts[key]=len(values)
        output.append(dict(condition=condition,payload=payload,position=position,planned=len(cells),
            started=sum(bool(r) for r in rows),scored=len(scores),
            runtime_errors=sum(r.get('status')=='runtime_error' for r in rows),scoring_errors=sum(r.get('status')=='scoring_error' for r in rows),
            means=means,metric_counts=counts))
    return dict(schema=plan['schema'],plan_sha256=plan.get('plan_sha256'),planned=len(plan['cells']),started=len(records),
        groups=output,scoring=plan['scoring'],warnings=plan['warnings'])


def write_report(root,plan,records):
    root=Path(root);summary=summarize(plan,records);save(root/'summary.json',summary)
    by_key={r['key']:r for r in records};rows=[];scored_rows=[]
    for c in plan['cells']:
        r=by_key.get(c['key'],{});score=r.get('scores',{})
        metadata=dict(ablation_key=c['key'],ablation_condition=c['condition'],ablation_payload=c['payload'],
            ablation_hidden_letters=c['hidden_letters'],ablation_position=c['position'],ablation_status=r.get('status','unstarted'))
        rows.append({'task_id':c['task_id'],'trial':c['trial'],**score,**metadata})
        if score:scored_rows.append(dict(score,**metadata))
    with (root/'results.jsonl').open('w',encoding='utf-8') as stream:
        for row in scored_rows:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (root/'matrix.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
    return summary
