# typeslop demo: a real Claude Code session, recorded with VHS (github.com/charmbracelet/vhs).
#
# Re-record from the repo root with TYPESAFE_API_KEY exported (it reaches the hook, never the screen):
#   mise x vhs@0.11.0 ttyd@latest ffmpeg@latest -- vhs docs/demo.tape
# vhs 0.12.0 exits 0 without writing output: https://github.com/charmbracelet/vhs/issues/787
# Needs git, python3, a logged-in `claude`, and access to hanneslipusch/typeslop.
# Set VHS_NO_SANDBOX=true where Chromium's sandbox is unavailable.
# The agent is live, so takes differ: it may fix after the per-edit note or argue instead of fixing.
# Keep a take that shows the block, the fix and a passing check.

Output docs/demo.gif

Set Shell bash
Set FontSize 20
Set Width 1000
Set Height 720
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms
Set PlaybackSpeed 1.5
Set WaitTimeout 90s

# Setup, off screen: a throwaway repo with the plugin installed at project scope, its own
# log, and settings from this project only so personal hooks and plugins stay out.
Hide
# A recording started from inside Claude Code must not inherit its session variables.
Type "unset ${!CLAUDE@} AI_AGENT"
Enter
Wait
Type "T=$(mktemp -d) && mkdir $T/app && cd $T/app && git init -q -b main && echo Y29uc3QgQkFTRSA9ICJodHRwczovL2FwaS5leGFtcGxlLmNvbSI7CgpleHBvcnQgYXN5bmMgZnVuY3Rpb24gZ2V0SnNvbjxUPihwYXRoOiBzdHJpbmcpOiBQcm9taXNlPFQ+IHsKICBjb25zdCByZXMgPSBhd2FpdCBmZXRjaChgJHtCQVNFfSR7cGF0aH1gKTsKICBpZiAoIXJlcy5vaykgdGhyb3cgbmV3IEVycm9yKGAke3BhdGh9OiAke3Jlcy5zdGF0dXN9YCk7CiAgcmV0dXJuIHJlcy5qc29uKCkgYXMgUHJvbWlzZTxUPjsKfQo= | base64 -d > api.ts"
Enter
Wait
Type "claude plugin marketplace add hanneslipusch/typeslop --scope project >/dev/null && claude plugin marketplace update typeslop >/dev/null && claude plugin install typeslop@typeslop --scope project >/dev/null"
Enter
Wait
Type "git add -A && git -c user.name=demo -c user.email=demo@example.com commit -qm init && export XDG_STATE_HOME=$T/state"
Enter
Wait
Type "alias claude='claude --setting-sources project,local --permission-mode acceptEdits --disallowedTools Bash --model haiku'"
Enter
Wait
Type `alias typeslop="$(ls -td ~/.claude/plugins/cache/typeslop/typeslop/*/ | head -1)bin/typeslop"`
Enter
Wait
# Accept the folder-trust dialog, then relaunch on a clean screen and let the startup notices fade.
Type "claude"
Enter
Sleep 6s
Down
Enter
Sleep 5s
Ctrl+C
Ctrl+C
Sleep 2s
Type "clear && claude"
Enter
Sleep 12s
Show

Type "Add a fetchWithRetry helper to api.ts"
Sleep 500ms
Enter
Sleep 45s
Ctrl+C
Ctrl+C
Sleep 1s
Type "typeslop check"
Enter
Wait
Sleep 6s
