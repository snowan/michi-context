from pathlib import Path
import json
import os
import tempfile

BASE_DIR = Path.home() / ".michi-context"
CLAUDE_DIR = Path.home() / ".claude"


def get_base_dir() -> Path:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    return BASE_DIR


def get_sessions_dir(project: str) -> Path:
    d = get_base_dir() / "sessions" / project
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_learnings_dir() -> Path:
    d = get_base_dir() / "learnings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_state() -> dict:
    state_file = get_base_dir() / ".state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"captured_sessions": {}}


def save_state(state: dict) -> None:
    state_file = get_base_dir() / ".state.json"
    atomic_write(state_file, json.dumps(state, indent=2))


def atomic_write(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def project_name_from_path(cwd: str) -> str:
    return Path(cwd).name


def claude_project_key(cwd: str) -> str:
    resolved = str(Path(cwd).resolve())
    return resolved.replace("/", "-").replace(".", "-")


def find_claude_session_files(cwd: str) -> list[Path]:
    key = claude_project_key(cwd)
    project_dir = CLAUDE_DIR / "projects" / key
    if not project_dir.exists():
        return []
    return sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def register_project(cwd: str) -> None:
    state = get_state()
    key = claude_project_key(cwd)
    name = project_name_from_path(cwd)
    state.setdefault("project_map", {})[key] = {"name": name, "path": str(Path(cwd).resolve())}
    save_state(state)


def project_name_from_key(dir_key: str) -> str | None:
    state = get_state()
    entry = state.get("project_map", {}).get(dir_key)
    return entry["name"] if entry else None
