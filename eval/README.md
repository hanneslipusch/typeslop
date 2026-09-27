# eval

How often typeslop would send an agent back, on code we trust and on code we expect to be
slop. Run it before you change `rubric.json` or the thresholds.

| set | what it is | should |
|---|---|---|
| `good` | 150 diffs from ten hand-maintained repos, before November 2022 | rarely flag |
| `slop` | about 200 diffs from unreviewed Claude Code commits | often flag |
| `smellbench planted` / `repaired` | [SmellBench](https://huggingface.co/datasets/critical88/SmellBench) smells and their fixes | often / rarely flag |

```
uv run eval/build.py good          # once; sets live in ~/.cache/typeslop-eval
uv run eval/build.py slop          # about 30 minutes, GitHub rate limits
uv run eval/build.py smellbench
uv run eval/report.py [rubric.json]   # needs a Jev key; about $0.10 per new rubric, cached after
```

Rewording the questions with GEPA found nothing beyond noise. The labels are the limit:
much unreviewed agent code is fine.
