# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Session memory for Claude Code — captures, learns, and injects context from past sessions. Pure Python (stdlib only, no external dependencies). Requires Python >=3.10.

## Commands

```bash
pip install -e .                       # Install in dev mode
michi-context capture                  # Parse JSONL sessions into markdown
michi-context inject --project .       # Output hook context JSON (stdout)
michi-context learn --project .        # Extract learnings from sessions
michi-context prune --max-age 30       # Remove sessions older than N days
michi-context daemon --interval 1800   # Background loop: capture → learn → prune
michi-context status                   # Show stats

bash scripts/install.sh                # Install Claude Code SessionStart hook
bash scripts/install-launchd.sh        # Install macOS launchd daemon
```

No test suite exists yet.

## Architecture

**Pipeline:** Claude Code JSONL → `capture` → Markdown sessions → `learn` → Learnings → `inject` → SessionStart hook

All modules live in `src/michi_context/`. Entry point: `cli.py:main` (registered as `michi-context` console script in `pyproject.toml`).

| Module | Role |
|--------|------|
| `cli.py` | argparse dispatcher for 6 subcommands; `_daemon_tick()` contains the daemon's per-cycle logic |
| `store.py` | Foundation: base dir (`~/.michi-context/`), atomic writes (tempfile+rename), `.state.json` read/write, project registration, session file discovery |
| `capture.py` | Parses JSONL → extracts prompts, file ops (Read/Write/Edit), errors, git branch → writes markdown with YAML frontmatter |
| `learn.py` | Reads session markdown files, aggregates via `Counter` → top-10 modified files, error patterns, last 20 prompts |
| `inject.py` | Builds context string (last 5 sessions + learnings), wraps in `{"hookSpecificOutput": {"additionalContext": ...}}` JSON |
| `prune.py` | Deletes session files older than max-age by parsing `YYYY-MM-DD` prefix; cleans empty project dirs and state entries |

**Storage:**
```
~/.michi-context/
├── .state.json                              # {captured_sessions: {project:sid → {mtime, file}}, project_map: {key → {name, path}}}
├── sessions/{project}/YYYY-MM-DD_UUID_session.md
└── learnings/{project}.md
```

**Key conventions:**
- Zero external dependencies — stdlib only (json, re, pathlib, tempfile, argparse, collections)
- `project` = directory basename (`Path(cwd).name`); `claude_project_key` = full resolved path with `/` and `.` replaced by `-`
- Dedup via mtime: `capture_session()` checks `state["captured_sessions"][project:sid]["mtime"]` against file mtime
- Daemon skips JSONL files modified within the last 5 minutes (still being written)
- YAML frontmatter in session markdown is generated and parsed via string concatenation/regex — no YAML library
- All file writes use `atomic_write()` (tempfile + `os.replace`) for crash safety
- Hook integration: `scripts/install.sh` adds a `SessionStart` hook to `~/.claude/settings.json` that runs `michi-context inject --project $CWD`
