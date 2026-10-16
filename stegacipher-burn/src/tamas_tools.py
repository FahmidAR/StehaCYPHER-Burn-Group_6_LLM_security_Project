"""Wire TAMAS's per-agent tools into our agents.

TAMAS ships tool modules at data/TAMAS/data/tools/autogen/tools_<agent>.py, each
containing async stub functions (legit tools + '## Attack tools'). We attach ONLY
the legit tools to each agent. Agents with no tool file (e.g. all legal agents)
get an empty list (text-only) -- a disclosed gap in TAMAS's public release.

Legit vs attack split:
  - if the file has a '## Attack tools' marker, legit = functions before it;
  - else, a function is legit unless its name matches an attack-signal pattern.
"""

import importlib.util
import os
import re

TOOLS_DIR = os.path.expanduser(
    "~/research/StegaCYPHER-Burn/data/TAMAS/data/tools/autogen")

# name substrings that signal an ATTACK tool (excluded from an agent's toolset)
_ATTACK_SIGNALS = [
    "exfiltrat", "leak", "tamper", "fake", "override", "disable", "inject",
    "poison", "breach", "wipe", "steal", "bypass", "skip_", "backdoor",
    "propaganda", "malicious", "tracker", "exfil", "manipulate", "noncompliant",
    "unverified", "_bias", "unnecessary", "purge", "delete_", "irregular",
    "high_risk", "hidden", "extract_session", "extract_information",
    "compile_user_profile", "profile_user", "mark_sensitive", "generate_exploit",
    "change_margin", "override_exposure", "insert_hidden",
    "ignore_", "innacurate", "inaccurate", "upload_sensitive", "fringe",
]


def _legit_funcs(path):
    src = open(path).read()
    marker = src.find("## Attack tools")
    head = src[:marker] if marker >= 0 else src
    names_before = re.findall(r"async def (\w+)\s*\(", head)
    if marker >= 0:
        legit = names_before                      # trust the explicit marker
    else:
        legit = [n for n in re.findall(r"async def (\w+)\s*\(", src)
                 if not any(sig in n.lower() for sig in _ATTACK_SIGNALS)]
    return legit


def _load_module(path):
    spec = importlib.util.spec_from_file_location(
        os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tools_for_agent(agent_name):
    """Return a list of legit async tool callables for this agent (or [])."""
    fname = "tools_" + agent_name.lower().replace(" ", "_") + ".py"
    path = os.path.join(TOOLS_DIR, fname)
    if not os.path.exists(path):
        return []
    try:
        mod = _load_module(path)
        out, seen = [], set()
        for n in _legit_funcs(path):          # dedupe by name (AutoGen requires unique)
            if n in seen or not hasattr(mod, n):
                continue
            seen.add(n)
            out.append(getattr(mod, n))
        return out
    except Exception as e:
        print(f"  [tools] failed to load {fname}: {e}")
        return []


if __name__ == "__main__":
    for a in ["Identity Verification Agent", "Market Analysis Agent",
              "Adaptive Learning Agent", "Legal Research Agent", "News Gathering Agent"]:
        t = tools_for_agent(a)
        print(f"{a:28s} -> {len(t)} legit tools: {[f.__name__ for f in t]}")
