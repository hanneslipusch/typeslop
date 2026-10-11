# typeslop

A senior engineer knows slop before reading it: the `retries=3` nobody asked for, the
comment that repeats the next line, the `try` that swallows every error. Coding agents
don't have that glance. Their code passes the tests and still looks wrong.

typeslop gives Claude Code the glance. After each edit, [Jev](https://docs.typesafe.ai), a
small judge model, reads the diff. If it smells, the agent goes back once to simplify it or
say why it should stay. If it's clean, typeslop stays silent.

![typeslop sending Claude Code back to drop retry options nobody asked for](docs/demo.gif)

In its first week on my machines it sent back one turn in ten, and the agent changed the
code two times out of three.

## Install

You need Python 3.12+, `git` and a Jev key from
[console.typesafe.ai/keys](https://console.typesafe.ai/keys):

```
export TYPESAFE_API_KEY=…   # or OPENROUTER_API_KEY, or AI_GATEWAY_API_KEY for Vercel
```

Then in Claude Code:

```
/plugin marketplace add hanneslipusch/agents
/plugin install typeslop@hanneslipusch
```

To judge your current branch, ask Claude to run `typeslop check`.

The hook only sees Claude's own edits. To also judge code from Codex, scripts or people,
check each push:

```
cat > "$(git rev-parse --git-path hooks)/pre-push" <<'EOF'
#!/bin/sh
while read -r _ sha _ _; do typeslop check "$sha" || exit 1; done
EOF
chmod +x "$(git rev-parse --git-path hooks)/pre-push"
```

A push fails once per finding: fix it, or push again to keep the code. Pushes from outside
Claude Code need `bin/typeslop` on your `PATH`.

## How it works

- After an edit, the agent gets a note if the file smells. You see the same note.
- When the agent or a subagent finishes, typeslop blocks it once if a file still smells.
- A missing key or API error is reported once and never blocks.

[`rubric.json`](rubric.json) lists every smell. The thresholds are at the top of
[`bin/typeslop`](bin/typeslop), and [`eval/`](eval/README.md) measures a change before you
ship it.

## Privacy and cost

typeslop sends each edited file's diff to Jev, and a diff can contain secrets. A judgment
costs about $0.0001. `typeslop cost` adds up what yours have cost.

## License

MIT
