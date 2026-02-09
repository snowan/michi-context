# michi-context MVP Implementation

## Completed
- [x] Project scaffold (pyproject.toml, `pip install -e .`, CLI entry point)
- [x] Storage layer (store.py) — base dir, sessions dir, state tracking, Claude project key
- [x] Session capture (capture.py) — JSONL parsing, file ops extraction, markdown summarization
- [x] Context injection (inject.py) — recent sessions + learnings → JSON for hooks
- [x] Pruning (prune.py) — date-based old session cleanup
- [x] Learning extraction (learn.py) — file frequency, error patterns, recent work
- [x] CLI (cli.py) — capture, inject, prune, learn, daemon, status subcommands
- [x] Install script (scripts/install.sh) — Claude Code SessionStart hook
- [x] Daemon setup (scripts/install-launchd.sh) — macOS launchd service
- [x] E2E verification — all commands verified on real session data

## Fixes Applied
- Fixed `claude_project_key()` to replace dots with `-` (matching Claude Code's actual format)
- Fixed session ID extraction to use JSONL filename stem instead of first `sessionId` in content (avoids cross-session contamination from `file-history-snapshot` entries)
- Fixed pyproject.toml build-backend from legacy path to `setuptools.build_meta`

## Verification Results
- `pip install -e .` — OK
- `michi-context --help` — OK, all subcommands listed
- `michi-context capture` — captured 2 sessions from real Claude Code data
- `michi-context inject` — valid JSON output with 3.8KB context
- `michi-context learn` — extracted 10 file patterns, 3 error patterns from 2 sessions
- `michi-context prune` — correctly skips recent sessions
- `michi-context status` — shows 1 project, 2 sessions, 1 learning, 3.1KB
