"""The decision on plain data, the diff on real git, and the whole hook on real transcripts.

Each test guards a failure seen in production: an agent sent back twice for one file, or
again for a finding it already answered; a stop that re-paid for a score its edit already
had; a note repeated on every edit; a dead key that looked like a quiet hook; a linked worktree judged as one untracked whole file; scratch
files outside any repo judged against whatever repo the shell stood in; a torn transcript
record that crashed every hook for the rest of its session.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BIN = str(Path(__file__).parent.parent / "bin/typeslop")
loader = importlib.machinery.SourceFileLoader("typeslop", BIN)
typeslop = importlib.util.module_from_spec(importlib.util.spec_from_loader("typeslop", loader))
loader.exec_module(typeslop)

DIFF = {"repo": "/r", "file": "slop.py", "diff": "+x\n" * 20, "lines": 20, "hash": "h1"}
LOW = {"score": 1.2, "level": "needs rewrite", "confidence": 0.9, "comments": 0.5, "comments_confidence": 0.9,
       "smells": [["verbose", 0.9]]}
CLEAN = {"score": 3.2, "level": "clean", "confidence": 0.9, "comments": 0.5, "comments_confidence": 0.9, "smells": []}


def run(kind, memory, verdicts, **event):
    records, output = typeslop.decide({"hook_event_name": kind, "session_id": "s", **event}, [DIFF], memory, verdicts)
    return records, output or {}


def test_a_low_score_notes_once_blocks_once_and_never_twice():
    edit, note = run("PostToolUse", [], {"h1": {**LOW, "tokens": 900}})
    assert "slop.py  1.2/4 needs rewrite\n  - verbose (0.90): " in note["hookSpecificOutput"]["additionalContext"]
    assert note["systemMessage"] == note["hookSpecificOutput"]["additionalContext"], "the user must see what the agent sees"
    assert run("PostToolUse", edit, {"h1": LOW})[1] == {}, "a note repeats on every edit"

    stop, block = run("Stop", edit, {})
    assert block["decision"] == "block", "a stop must reuse the edit's score, not re-judge"
    assert "tokens" not in stop[0], "a reused score was counted as paid twice"
    assert run("Stop", edit + stop, {}) == ([], {}), "a stop judged the same diff twice"

    after, output = run("Stop", edit + stop, {}, stop_hook_active=True, last_assistant_message="It is a fixture.")
    assert "decision" not in output
    assert after[0]["justification"] == "It is a fixture."


def test_a_file_is_blocked_again_only_for_a_new_finding():
    def stop(memory, version, verdict):
        return typeslop.decide({"hook_event_name": "Stop", "session_id": "s"}, [{**DIFF, "hash": version}], memory, {version: verdict})
    first, _ = stop([], "h1", LOW)
    assert stop(first, "h2", LOW)[1] is None, "the same finding blocked the file again"
    assert stop(first, "h3", {**LOW, "smells": [["loose typing", 0.9]]})[1]["decision"] == "block", "a new finding went through"


def test_clean_code_passes_and_comment_prose_alone_flags():
    assert run("Stop", [], {"h1": CLEAN})[1] == {}, "clean code must pass silently"
    _, output = run("Stop", [], {"h1": {**CLEAN, "comments": 3.6}})
    assert "  - too much comment prose (3.6/4, 90% sure)" in output["reason"]


def test_a_low_score_blocks_only_when_jev_is_sure_and_unsure_prose_is_a_nitpick():
    assert "decision" not in run("Stop", [], {"h1": {**CLEAN, "score": 2.1, "confidence": 0.45}})[1]
    _, output = run("Stop", [], {"h1": {**CLEAN, "score": 2.1, "confidence": 0.8}})
    assert "  - hard to read (2.1/4, 80% sure): simplify" in output["reason"]
    _, output = run("Stop", [], {"h1": {**CLEAN, "comments": 2.4, "comments_confidence": 0.5}})
    assert "  - nitpick: too much comment prose (2.4/4, 50% sure)" in output["reason"]


def test_a_broken_judge_warns_the_user_once_per_session_and_never_blocks():
    error = typeslop.JudgeError(typeslop.NO_KEY)
    first, output = run("Stop", [], {"h1": error})
    assert output == {"systemMessage": f"typeslop could not judge: {typeslop.NO_KEY}"}
    assert run("Stop", first, {"h1": error})[1] == {}


@pytest.fixture
def repo(tmp_path):
    def git(*args, cwd=tmp_path / "repo"):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True)
    (tmp_path / "repo").mkdir()
    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "init")
    return tmp_path / "repo", git


def test_a_file_is_diffed_against_its_own_repo(repo, tmp_path):
    root, git = repo
    worktree = root / ".claude/worktrees/wt"
    git("worktree", "add", "-q", str(worktree))
    deep = worktree / "deep.py"
    deep.write_text("".join(f"line{i}\n" for i in range(60)))
    git("add", "deep.py", cwd=worktree)
    git("commit", "-q", "-m", "deep", cwd=worktree)
    deep.write_text("".join(f"line{i}{'!' if i < 10 else ''}\n" for i in range(60)))

    diff = typeslop.diff_for(str(deep))
    assert (diff["repo"], diff["file"], diff["lines"] < 30) == (str(worktree), "deep.py", True)

    (root / "new.py").write_text("x = 1\n" * 12)
    assert typeslop.diff_for(str(root / "new.py"))["diff"].startswith("diff --git a/new.py")

    (root / ".gitignore").write_text("local_settings.py\n")
    (root / "local_settings.py").write_text("KEY = 1\n" * 12)
    assert typeslop.diff_for(str(root / "local_settings.py")) is None, "an ignored file was sent whole"

    (tmp_path / "scratch.py").write_text("x = 1\n" * 12)
    assert typeslop.diff_for(str(tmp_path / "scratch.py")) is None, "a file outside any repo was judged"


def hook(event, state):
    """The script as Claude Code runs it: the event on stdin, no API key, the log under state."""
    env = {k: v for k, v in os.environ.items() if k not in {key for key, _, _ in typeslop.PROVIDERS}}
    out = subprocess.run([sys.executable, BIN, "hook"], input=json.dumps(event), capture_output=True, text=True,
                         env={**env, "XDG_STATE_HOME": str(state)}, check=True).stdout
    return json.loads(out) if out else {}


def test_the_hook_finds_an_edit_past_a_torn_transcript_record(repo, tmp_path):
    root, _ = repo
    (root / "a.py").write_text("x = 1\n" * 12)
    edit = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": str(root / "a.py"), "new_string": "x\u2028y"}}]}}
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"type":"user","message":{"content":"Exit co{"type":"user"}\n'
                          + json.dumps(edit, ensure_ascii=False) + "\n")
    output = hook({"hook_event_name": "Stop", "session_id": "s", "transcript_path": str(transcript)}, tmp_path)
    assert output == {"systemMessage": f"typeslop could not judge: {typeslop.NO_KEY}"}, "the edit was never found"


def test_the_hook_never_crashes_on_this_machines_transcripts(tmp_path):
    transcripts = sorted(Path.home().glob(".claude/projects/*/*.jsonl"), key=os.path.getmtime)[-30:]
    if not transcripts:
        pytest.skip("no Claude Code transcripts here")
    for t in transcripts:
        output = hook({"hook_event_name": "Stop", "session_id": t.stem, "transcript_path": str(t)}, tmp_path)
        assert "crashed" not in output.get("systemMessage", ""), f"{t}: {output}"


def test_cost_counts_paid_judgments_and_excludes_reused_scores(tmp_path):
    def cost():
        return subprocess.run([sys.executable, BIN, "cost"], capture_output=True, text=True,
                              env={**os.environ, "XDG_STATE_HOME": str(tmp_path)}, check=True).stdout

    assert cost() == "0 judgments, 0 input tokens, $0.0000\n"
    edit, _ = run("PostToolUse", [], {"h1": {**LOW, "tokens": 9000}})
    stop, _ = run("Stop", edit, {})
    typeslop.append_jsonl(tmp_path / "typeslop/log.jsonl",
                          edit + stop + [{"event": "check", "tokens": 1000}, {"warned": True}])
    assert cost() == "2 judgments, 10,000 input tokens, $0.0004\n"
