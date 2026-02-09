import json

from .store import get_sessions_dir, get_learnings_dir


def find_relevant_sessions(project: str, limit: int = 5) -> list[str]:
    sessions_dir = get_sessions_dir(project)
    files = sorted(sessions_dir.glob("*_session.md"), key=lambda p: p.name, reverse=True)
    return [f.read_text() for f in files[:limit]]


def build_context(project: str) -> str:
    parts = []

    sessions = find_relevant_sessions(project)
    if sessions:
        parts.append(f"# Recent Sessions ({len(sessions)})\n")
        for i, s in enumerate(sessions, 1):
            parts.append(f"### Session {i}")
            parts.append(s)
            parts.append("")

    learnings_file = get_learnings_dir() / f"{project}.md"
    if learnings_file.exists():
        parts.append("# Project Learnings\n")
        parts.append(learnings_file.read_text())

    return "\n".join(parts)


def format_for_hook(project: str) -> str:
    context = build_context(project)
    if not context.strip():
        return ""
    payload = {
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }
    return json.dumps(payload)
