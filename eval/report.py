"""How often typeslop's findings are right, on diffs a strict reviewer labelled slop or not.

  uv run eval/report.py [rubric.json]    # with a Jev key exported

Each labelled diff is fetched once from GitHub and cached. Pass a rubric variant to compare
it with the shipped rubric.json; only its uncached diffs are paid for.
"""

import json
import re
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jev import DATA, USAGE, ask_all, typeslop

HERE = Path(__file__).resolve().parent


def commit_diff(source: str) -> str:
    repo, sha = source.split("@")
    path = DATA / "commits" / f"{repo.replace('/', '_')}@{sha}.diff"
    if not path.exists():
        with urllib.request.urlopen(f"https://github.com/{repo}/commit/{sha}.diff") as response:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.read())
    return path.read_text()


def file_diff(label: dict) -> str:
    """The label's file out of its commit's diff; the label's path starts with the repo name."""
    file = label["file"].split("/", 1)[1]
    parts = re.split(r"(?m)^(?=diff --git )", commit_diff(label["source"]))
    return next(p for p in parts if p.startswith(f"diff --git a/{file} b/{file}\n"))


rubric_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "rubric.json"
rubric = json.loads(rubric_path.read_text())
labels = typeslop.read_jsonl(HERE / "labels.jsonl")
with ThreadPoolExecutor(8) as pool:
    cases = [{"file": label["file"], "diff": diff} for label, diff in zip(labels, pool.map(file_diff, labels), strict=True)]

slop = [label["slop"] for label in labels]
findings = [{n for _, n, _ in typeslop.findings_of(typeslop.verdict_of(a))} for a in ask_all(cases, rubric)]
flagged = sum(bool(f) for f in findings)
hits = sum(bool(f) and s for f, s in zip(findings, slop, strict=True))
print(f"rubric: {rubric_path}\n{len(cases)} labelled diffs, {sum(slop)} of them slop\n")
print(f"precision {hits / flagged:.0%}   a flag is right")
print(f"recall    {hits / sum(slop):.0%}   slop gets flagged\n")
fired = Counter(n for f in findings for n in f)
right = Counter(n for f, s in zip(findings, slop, strict=True) if s for n in f)
for name, n in fired.most_common():
    print(f"{name:<26} {right[name]:>3} of {n} on slop")
calls, tokens, dollars = typeslop.cost([r["input_tokens"] for r in typeslop.read_jsonl(USAGE)])
print(f"\nJev spend so far: {calls} calls, {tokens:,} input tokens, ${dollars:.2f}")
