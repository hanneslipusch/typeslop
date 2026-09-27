"""Build the eval sets under ~/.cache/typeslop-eval/sets, one per-file diff per line.

  uv run eval/build.py good         # curated human code, before ChatGPT
  uv run eval/build.py slop         # unreviewed Claude Code commits (slow: GitHub rate limits)
  uv run eval/build.py smellbench   # planted textbook smells and their human repairs

Each line is {"set", "source", "file", "diff"}, shaped like the hook's `git diff`.
"""

import json
import random
import re
import subprocess
import sys
import time
import urllib.request

from jev import DATA, typeslop

SETS, REPOS = DATA / "sets", DATA / "repos"
CODE = (".py", ".ts", ".tsx", ".js")
SKIP = ("test", "docs/", "example", "bench", ".d.ts", "vendor", "dist/", "scripts/", "generated")
# Maintained by hand, with a strong house style, and old enough to predate coding agents.
CURATED = ["pallets/flask", "pallets/click", "encode/httpx", "python-attrs/attrs", "Textualize/rich",
           "colinhacks/zod", "preactjs/preact", "sindresorhus/ky", "honojs/hono", "trpc/trpc"]
BEFORE_AGENTS = "2022-11-01"
SIZE = 150


def ours(path: str, added: int, changed: int) -> bool:
    return path.endswith(CODE) and not any(s in path for s in SKIP) and added >= 8 and changed <= 200


def fits(diff: str) -> bool:
    """The hook's size window, minus minified or bundled files: no human reads a 300-character line."""
    return typeslop.MIN_LINES <= diff.count("\n") <= typeslop.MAX_LINES and max(map(len, diff.splitlines())) <= 300


def git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def good() -> list[dict]:
    """One file from each of 15 random pre-agent commits per curated repo."""
    cases = []
    for name in CURATED:
        repo = REPOS / name.split("/")[1]
        if not repo.exists():
            subprocess.run(["git", "clone", "-q", "--no-checkout", f"https://github.com/{name}", str(repo)], check=True)
        commits = git(repo, "log", "--no-merges", f"--until={BEFORE_AGENTS}", "--numstat", "--format=@%H").split("@")[1:]
        random.shuffle(commits)
        picked = []
        for entry in commits:
            sha, *stats = entry.strip().split("\n")
            files = [s.split("\t") for s in stats if s.count("\t") == 2 and not s.startswith("-")]
            files = [p for a, d, p in files if ours(p, int(a), int(a) + int(d))]
            if files and fits(diff := git(repo, "show", "--format=", sha, "--", path := random.choice(files))):
                picked.append({"source": f"{name}@{sha[:10]}", "file": f"{repo.name}/{path}", "diff": diff})
            if len(picked) == SIZE // len(CURATED):
                break
        cases += picked
    return cases


def gh(path: str, *fields: str) -> dict:
    """GitHub API GET that waits out rate limits and fails loudly on anything else."""
    for _ in range(10):
        out = subprocess.run(["gh", "api", "-X", "GET", path, *(a for f in fields for a in ("-f", f))],
                             capture_output=True, text=True, check=False)
        if out.returncode == 0:
            return json.loads(out.stdout)
        if "rate limit" in (out.stdout + out.stderr).lower():
            time.sleep(60)
            continue
        raise RuntimeError(f"gh api {path}: {out.stderr.strip()}")
    raise RuntimeError(f"gh api {path}: still rate limited after 10 minutes")


def slop() -> list[dict]:
    """One file from one commit per repo, among commits carrying the Claude Code trailer.

    The trailer means an agent wrote the commit; one per repo keeps any single project's style
    from dominating. Search returns at most 1000 hits per query, so it walks week by week.
    """
    hits, seen = [], set()
    for week in range(20):
        start = time.strftime("%Y-%m-%d", time.gmtime(time.time() - (week + 1) * 7 * 86400))
        end = time.strftime("%Y-%m-%d", time.gmtime(time.time() - week * 7 * 86400))
        for page in (1, 2):
            found = gh("search/commits", f'q="Generated with Claude Code" committer-date:{start}..{end}',
                       "per_page=100", f"page={page}")
            hits += [(h["repository"]["full_name"], h["sha"]) for h in found["items"] if not h["repository"]["fork"]]
            time.sleep(2.5)  # search allows 30 requests a minute
    random.shuffle(hits)
    cases = []
    for repo, sha in hits:
        if repo in seen:
            continue
        seen.add(repo)
        files = [f for f in gh(f"repos/{repo}/commits/{sha}").get("files", [])
                 if f.get("patch") and ours(f["filename"], f["additions"], f["changes"])]
        if files:
            f = random.choice(files)
            diff = f"diff --git a/{f['filename']} b/{f['filename']}\n--- a/{f['filename']}\n+++ b/{f['filename']}\n{f['patch']}\n"
            if fits(diff):
                cases.append({"source": f"{repo}@{sha[:10]}", "file": f"{repo.split('/')[1]}/{f['filename']}", "diff": diff})
                print(f"\r{len(cases)} slop diffs from {len(seen)} repos", end="", file=sys.stderr)
        if len(cases) == 2 * SIZE:
            break
    print(file=sys.stderr)
    return cases


def smellbench() -> list[dict]:
    """critical88/SmellBench (Apache-2.0): each file an agent's planted smell touched, and its repair."""
    url = "https://huggingface.co/datasets/critical88/SmellBench/resolve/main/smell_codes.json"
    with urllib.request.urlopen(url) as response:
        rows = json.load(response)

    def per_file(diff):
        parts = re.split(r"(?m)^(?=diff --git )", diff)
        return {re.match(r"diff --git a/(\S+)", p).group(1): p for p in parts if p.startswith("diff --git")}

    cases = []
    for row in rows:
        planted, repaired = per_file(row["smell_content"]), per_file(row["gt_content"])
        for path in sorted(planted.keys() & repaired.keys()):
            if path.endswith(CODE) and fits(planted[path]) and fits(repaired[path]):
                source = f"{row['instance_id']} ({row['type']})"
                cases.append({"set": "smellbench planted", "source": source, "file": path, "diff": planted[path]})
                cases.append({"set": "smellbench repaired", "source": source, "file": path, "diff": repaired[path]})
    return cases


if __name__ == "__main__":
    random.seed(7)
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    build = {"good": good, "slop": slop, "smellbench": smellbench}.get(name)
    if build is None:
        sys.exit(__doc__)
    SETS.mkdir(parents=True, exist_ok=True)
    cases = [{"set": name, **c} if "set" not in c else c for c in build()]
    (SETS / f"{name}.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases))
    print(f"{len(cases)} diffs → {SETS / name}.jsonl")
