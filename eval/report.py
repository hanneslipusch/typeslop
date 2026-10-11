"""How often typeslop's findings are right, on diffs a strict reviewer labelled slop or not.

  uv run eval/report.py [rubric.json]    # with a Jev key exported

Pass a rubric variant to compare it with the shipped rubric.json; only its uncached diffs are paid for.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from jev import DATA, USAGE, ask_all, typeslop

HERE = Path(__file__).resolve().parent
rubric_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "rubric.json"
rubric = json.loads(rubric_path.read_text())
labels = {(r["source"], r["file"]): r["slop"] for r in typeslop.read_jsonl(HERE / "labels.jsonl")}
cases = [c for f in sorted((DATA / "sets").glob("*.jsonl")) for c in typeslop.read_jsonl(f) if (c["source"], c["file"]) in labels]
if len(cases) < len(labels):
    sys.exit(f"{len(labels) - len(cases)} labelled diffs are missing from {DATA / 'sets'}")

slop = [labels[c["source"], c["file"]] for c in cases]
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
