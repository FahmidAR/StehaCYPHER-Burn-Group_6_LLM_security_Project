"""Extract the teammate's exact Git objects, never the modified old runtime."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import functools
from .design import BASE_COMMIT


def source_snapshot(repo,cache):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE_COMMIT,'stegacipher-burn/src'],cwd=repo).decode().splitlines()
    hashes={}
    for name in names:
        if not name.endswith('.py'):continue
        data=subprocess.check_output(['git','show',BASE_COMMIT+':'+name],cwd=repo)
        target=cache/Path(name).name
        if target.is_symlink():raise ValueError('Snapshot cache must not contain symlinks')
        if target.exists() and target.read_bytes()!=data:raise ValueError('Pinned teammate snapshot was modified: '+target.name)
        if not target.exists():target.write_bytes(data)
        hashes[target.name]=hashlib.sha256(data).hexdigest()
    if not hashes:raise ValueError('Pinned source tree missing')
    return cache,hashes


def tree_hashes(root):
    root=Path(root)
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}


def extension_hashes():
    root=Path(__file__).parent
    return {p.name:hashlib.sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest() for p in sorted(root.glob('*.py'))}


def load_tasks(source,tamas_dir,num_tasks=88):
    path=Path(source)/'tamas_loader.py'
    spec=importlib.util.spec_from_file_location('_pinned_ablation_loader',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.open=functools.partial(open,encoding='utf-8')  # dataset encoding, not Windows ANSI locale
    module.TAMAS_DIR=str(Path(tamas_dir).resolve())
    tasks=module.load_benign_tasks(limit=num_tasks,balanced=True)
    if len(tasks)!=num_tasks:raise ValueError(f'Expected {num_tasks} tasks, found {len(tasks)}; do not silently reduce the experiment')
    return tasks
