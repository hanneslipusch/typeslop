"""Judge every built set and show how often the hook would send the agent back.

  uv run eval/report.py [rubric.json]    # with a Jev key exported

The target: flag slop often and good code rarely. Pass a rubric variant to compare it with
the shipped rubric.json; only its uncached diffs are paid for.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from jev import DATA, USAGE, ask_all, typeslop

rubric_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "rubric.json"
rubric = json.loads(rubric_path.read_text())
sets: dict[str, list[dict]] = {}
for file in sorted((DATA / "sets").glob("*.jsonl")):
    for case in typeslop.read_jsonl(file):
        sets.setdefault(case["set"], []).append(case)
if not sets:
    sys.exit("no sets yet: run eval/build.py first")

print(f"rubric: {rubric_path}\n")
print(f"{'set':<22} {'diffs':>5} {'flagged':>8} {'sure':>6} {'mean score':>11}   top findings")
for name, cases in sets.items():
    verdicts = [typeslop.verdict_of(a) for a in ask_all(cases, rubric)]
    findings = [typeslop.findings_of(v) for v in verdicts]
    flagged = sum(bool(f) for f in findings)
    sure = sum(any(s for s, _, _ in f) for f in findings)
    top = Counter(n for f in findings for _, n, _ in f).most_common(3)
    print(f"{name:<22} {len(cases):>5} {flagged / len(cases):>8.0%} {sure / len(cases):>6.0%}"
          f" {sum(v['score'] for v in verdicts) / len(cases):>11.2f}   {', '.join(f'{n} {c}' for n, c in top)}")
calls, tokens, dollars = typeslop.cost([r["input_tokens"] for r in typeslop.read_jsonl(USAGE)])
print(f"\nJev spend so far: {calls} calls, {tokens:,} input tokens, ${dollars:.2f}")
