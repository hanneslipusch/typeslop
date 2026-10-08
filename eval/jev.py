"""Jev with a disk cache.

Cached answers are keyed by (rubric, file, diff), so re-reporting costs nothing and only a
changed rubric pays for new calls. Every paid call appends its token usage to usage.jsonl.
"""

import hashlib
import importlib.machinery
import importlib.util
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path.home() / ".cache/typeslop-eval"
CACHE, USAGE = DATA / "cache.jsonl", DATA / "usage.jsonl"

_loader = importlib.machinery.SourceFileLoader("typeslop", str(Path(__file__).resolve().parent.parent / "bin/typeslop"))
typeslop = importlib.util.module_from_spec(importlib.util.spec_from_loader("typeslop", _loader))
_loader.exec_module(typeslop)

_lock = threading.Lock()
_cache = {r["key"]: r["answers"] for r in typeslop.read_jsonl(CACHE)}


def _key(rubric: dict, file: str, diff: str) -> str:
    return hashlib.sha1(json.dumps([rubric, file, diff, "diff"]).encode()).hexdigest()


def _call(rubric: dict, file: str, diff: str) -> dict:
    reply = typeslop.ask(file, diff, 60, rubric)
    with _lock:
        typeslop.append_jsonl(USAGE, [reply["usage"]])
    return reply["answers"]


def ask_all(cases: list[dict], rubric: dict) -> list[dict]:
    """Raw Jev answers for each case's (file, diff), paying only for uncached ones."""
    keys = [_key(rubric, c["file"], c["diff"]) for c in cases]
    missing = {k: c for k, c in zip(keys, cases, strict=True) if k not in _cache}
    if missing:
        if typeslop.provider() is None:
            raise SystemExit(typeslop.NO_KEY)
        if len(missing) > 1:
            print(f"judging {len(missing)} diffs")
        with ThreadPoolExecutor(8) as pool:
            for k, answers in zip(missing, pool.map(lambda c: _call(rubric, c["file"], c["diff"]), missing.values()), strict=True):
                with _lock:
                    _cache[k] = answers
                    typeslop.append_jsonl(CACHE, [{"key": k, "answers": answers}])
    return [_cache[k] for k in keys]
