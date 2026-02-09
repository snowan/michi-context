# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Session memory for Claude Code — captures, learns, and injects context from past sessions. Pure Python (stdlib only, no external dependencies). Requires Python >=3.10.

## Commands

```bash
# Install in development mode
pip install -e .

# Run CLI
michi-context capture              # Parse JSONL sessions into markdown
michi-context inject --project .   # Output hook context JSON
michi-context learn --project .    # Extract learnings from sessions
michi-context prune --max-age 30   # Remove sessions older than N days
michi-context daemon --interval 1800  # Background loop: capture → learn → prune
michi-context status               # Show stats (projects, sessions, disk)

# Install Claude Code SessionStart hook
bash scripts/install.sh

# Install macOS launchd daemon
bash scripts/install-launchd.sh
```

No test suite exists yet.

## Architecture

**Data flow:** Claude Code JSONL → `capture` (parse) → Markdown sessions → `learn` (aggregate) → Learnings → `inject` (format for hook) → Claude Code SessionStart hook

**Modules** (`src/michi_context/`):

| Module | Role |
|--------|------|
| `cli.py` | argparse dispatcher — 6 subcommands |
| `store.py` | File/state foundation — base dir (`~/.michi-context/`), atomic writes, state JSON, session file discovery |
| `capture.py` | Parses Claude Code JSONL into markdown with YAML frontmatter (extracts prompts, file ops, errors, branch) |
| `learn.py` | Aggregates sessions into per-project learnings (frequent files, error patterns, recent prompts) |
| `inject.py` | Formats recent sessions + learnings as JSON for `hookSpecificOutput.additionalContext` |
| `prune.py` | Deletes sessions older than max-age by parsing date prefix from filename |

**Storage layout:**
```
~/.michi-context/
├── .state.json                          # mtime tracking, project registry
├── sessions/{project}/YYYY-MM-DD_UUID_session.md
└── learnings/{project}.md
```

**Key design choices:**
- File-based state with atomic writes (tempfile + rename) — no database
- Mtime tracking in `.state.json` prevents re-processing unchanged JSONL files
- Session files use YAML frontmatter parsed via regex (no YAML library)
- macOS-specific install scripts (bash, launchd)
