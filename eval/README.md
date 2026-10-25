# eval

How often typeslop's findings are right. Run it before you change `rubric.json` or the
thresholds.

[`labels.jsonl`](labels.jsonl) marks diffs as slop or not, with the smells and a reason.
A strict reviewer labelled each one before seeing Jev's answer. The diffs come from two sets:

| set | what it is |
|---|---|
| `good` | 150 diffs from ten hand-maintained repos, before November 2022 |
| `slop` | about 200 diffs from unreviewed Claude Code commits |

```
uv run eval/report.py [rubric.json]   # needs a Jev key; about $0.02 per new rubric, cached after
```

The first run fetches each labelled commit's diff from GitHub into `~/.cache/typeslop-eval`.
Who wrote the code says little: about a fifth of `good` and a third of `slop` is slop.
