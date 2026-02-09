from pathlib import Path
from datetime import datetime, timedelta
import re

from .store import get_base_dir, get_state, save_state

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")


def prune_old_sessions(max_age_days: int = 30) -> list[Path]:
    sessions_root = get_base_dir() / "sessions"
    if not sessions_root.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    pruned = []

    for session_file in sessions_root.rglob("*_session.md"):
        m = DATE_PREFIX_RE.match(session_file.name)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if file_date < cutoff:
            session_file.unlink()
            pruned.append(session_file)

    if pruned:
        state = get_state()
        captured = state.get("captured_sessions", {})
        pruned_paths = {str(p) for p in pruned}
        state["captured_sessions"] = {
            k: v for k, v in captured.items()
            if v.get("file") not in pruned_paths
        }
        save_state(state)

        for project_dir in sessions_root.iterdir():
            if project_dir.is_dir() and not any(project_dir.iterdir()):
                project_dir.rmdir()

    return pruned
