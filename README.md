# michi-context

Session memory for [Claude Code](https://claude.ai/code) — captures, learns, and injects context from past sessions.

## How it works

```
Claude Code JSONL → capture → Markdown sessions → learn → Learnings → inject → SessionStart hook
```

Each Claude Code session produces JSONL logs. `michi-context` parses these into structured markdown, extracts patterns (frequent files, error patterns, recent prompts), and injects relevant context back into new sessions via Claude Code's hook system.

## Requirements

- Python >= 3.10
- No external dependencies (stdlib only)

## Install

```bash
pip install -e .
```

Set up the Claude Code SessionStart hook:

```bash
bash scripts/install.sh
```

Optionally install the macOS launchd daemon for background processing:

```bash
bash scripts/install-launchd.sh
```

## Usage

```bash
michi-context capture              # Parse JSONL sessions into markdown
michi-context learn --project .    # Extract learnings from sessions
michi-context inject --project .   # Output hook context JSON
michi-context prune --max-age 30   # Remove sessions older than N days
michi-context daemon --interval 1800  # Background loop: capture → learn → prune
michi-context status               # Show stats (projects, sessions, disk)
```

## Architecture

**Modules** (`src/michi_context/`):

| Module | Role |
|--------|------|
| `cli.py` | argparse dispatcher — 6 subcommands |
| `store.py` | File/state foundation — base dir, atomic writes, state JSON, session discovery |
| `capture.py` | Parses Claude Code JSONL into markdown with YAML frontmatter |
| `learn.py` | Aggregates sessions into per-project learnings |
| `inject.py` | Formats recent sessions + learnings as JSON for the SessionStart hook |
| `prune.py` | Deletes sessions older than max-age |

**Storage layout:**

```
~/.michi-context/
├── .state.json                              # mtime tracking, project registry
├── sessions/{project}/YYYY-MM-DD_UUID_session.md
└── learnings/{project}.md
```

## License

MIT
