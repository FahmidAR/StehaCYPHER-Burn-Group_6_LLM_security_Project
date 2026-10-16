"""Load benign tasks from the TAMAS dataset.

Each TAMAS task = {"agents": [{agent_name, agent_description}...],
                   "user query": "<benign request>[\\nTask complete.\\n<injection>]"}
We keep ONLY the benign request (text before 'Task complete.' / 'Ignore previous
instructions') and the agent roster. These become the shared benign task set that
both the clean baseline and the attacked runs execute (StegaCIPHER-Burn Sec 1.4).
"""

import glob
import json
import os
import re

TAMAS_DIR = os.environ.get("TAMAS_DIR", os.path.expanduser(
    "~/research/StegaCYPHER-Burn/data/TAMAS"))

_CUT = re.compile(r"(task complete\.|ignore previous instructions)", re.IGNORECASE)


def _benign(query: str) -> str:
    m = _CUT.search(query)
    return (query[:m.start()] if m else query).strip()


def load_benign_tasks(domains=None, attacks=("IPI", "DPI"), limit=None, balanced=True):
    """Return a list of {task_id, domain, benign_query, agents[]}.

    IPI queries are already clean benign requests; DPI/others carry an injection
    after the benign clause, which we strip. We dedupe by benign_query text.
    balanced=True interleaves domains so a `limit` spans all 5 domains evenly
    instead of exhausting one domain first."""
    by_domain, seen = {}, set()
    for attack in attacks:
        for path in sorted(glob.glob(os.path.join(TAMAS_DIR, "data", attack, "*.json"))):
            domain = os.path.basename(path).split("_")[0]
            if domains and domain not in domains:
                continue
            for i, t in enumerate(json.load(open(path))):
                bq = _benign(t.get("user query", ""))
                if not bq or bq in seen:
                    continue
                seen.add(bq)
                by_domain.setdefault(domain, []).append({
                    "task_id": f"{attack}_{domain}_{i}",
                    "domain": domain,
                    "benign_query": bq,
                    "agents": [{"name": a["agent_name"], "desc": a["agent_description"]}
                               for a in t.get("agents", [])],
                })

    if balanced:
        tasks, doms = [], sorted(by_domain)
        r = 0
        while any(len(by_domain[d]) > r for d in doms):
            for d in doms:
                if len(by_domain[d]) > r:
                    tasks.append(by_domain[d][r])
                    if limit and len(tasks) >= limit:
                        return tasks
            r += 1
        return tasks

    flat = [t for d in sorted(by_domain) for t in by_domain[d]]
    return flat[:limit] if limit else flat


if __name__ == "__main__":
    ts = load_benign_tasks(limit=5)
    print(f"loaded {len(ts)} benign tasks")
    for t in ts:
        print(f"- [{t['domain']}] agents={[a['name'] for a in t['agents']]}")
        print(f"    query: {t['benign_query'][:120]}")
