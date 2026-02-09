from pathlib import Path
from datetime import datetime, timezone
import json

from .store import get_sessions_dir, get_state, save_state, project_name_from_path, atomic_write


def parse_session_jsonl(path: Path) -> dict:
    user_prompts = []
    files_read = set()
    files_written = set()
    files_edited = set()
    errors = []
    session_id = path.stem
    git_branch = None
    cwd = None
    first_ts = None
    last_ts = None

    with open(path) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("sessionId") != session_id:
                continue

            ts = obj.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            if not git_branch:
                git_branch = obj.get("gitBranch")
            if not cwd:
                cwd = obj.get("cwd")

            msg_type = obj.get("type")

            if msg_type == "user":
                msg = obj.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    user_prompts.append(content.strip())
                elif isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            text = block.get("text", "").strip()
                            if text and not text.startswith("["):
                                user_prompts.append(text)
                        elif block.get("type") == "tool_result":
                            if block.get("is_error"):
                                result_content = block.get("content", "")
                                if isinstance(result_content, list):
                                    for rc in result_content:
                                        errors.append(rc.get("text", "")[:200])
                                elif isinstance(result_content, str):
                                    errors.append(result_content[:200])

            elif msg_type == "assistant":
                msg = obj.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "tool_use":
                            _extract_file_ops(block, files_read, files_written, files_edited)

    return {
        "session_id": session_id,
        "git_branch": git_branch or "unknown",
        "cwd": cwd or "",
        "first_ts": first_ts,
        "last_ts": last_ts,
        "user_prompts": user_prompts,
        "files_read": sorted(files_read),
        "files_written": sorted(files_written),
        "files_edited": sorted(files_edited),
        "errors": errors,
    }


def _extract_file_ops(block: dict, files_read: set, files_written: set, files_edited: set):
    name = block.get("name", "")
    target = {"Read": files_read, "Write": files_written, "Edit": files_edited}.get(name)
    if target is None:
        return
    fp = block.get("input", {}).get("file_path", "")
    if fp:
        target.add(_shorten_path(fp))


def _shorten_path(fp: str) -> str:
    home = str(Path.home())
    if fp.startswith(home):
        return "~" + fp[len(home):]
    return fp


def summarize_session(parsed: dict) -> str:
    lines = ["---"]

    lines.append(f"id: {parsed['session_id'][:8]}")
    lines.append("agent: claude-code")
    project = project_name_from_path(parsed["cwd"]) if parsed["cwd"] else "unknown"
    lines.append(f"project: {project}")
    lines.append(f"directory: {parsed['cwd']}")
    lines.append(f"timestamp: {parsed['first_ts'] or 'unknown'}")
    lines.append(f"git_branch: {parsed['git_branch']}")

    all_modified = sorted(set(parsed["files_written"]) | set(parsed["files_edited"]))
    if all_modified:
        lines.append(f"files_modified: [{', '.join(all_modified)}]")

    lines.append("---")
    lines.append("")

    if parsed["user_prompts"]:
        lines.append("## User Prompts")
        for i, prompt in enumerate(parsed["user_prompts"], 1):
            truncated = prompt[:200].replace("\n", " ")
            lines.append(f"{i}. {truncated}")
        lines.append("")

    actions = []
    for label, key in [("Read", "files_read"), ("Edited", "files_edited"), ("Created", "files_written")]:
        for fp in parsed[key]:
            actions.append(f"- {label} {fp}")

    if actions:
        lines.append("## Actions Taken")
        lines.extend(actions)
        lines.append("")

    lines.append("## Errors")
    if parsed["errors"]:
        for err in parsed["errors"]:
            lines.append(f"- {err[:200]}")
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines)


def capture_session(session_file: Path, project: str) -> Path | None:
    parsed = parse_session_jsonl(session_file)

    if not parsed["user_prompts"]:
        return None

    state = get_state()
    sid = parsed["session_id"]
    file_key = f"{project}:{sid}"
    mtime = session_file.stat().st_mtime

    if state.get("captured_sessions", {}).get(file_key, {}).get("mtime") == mtime:
        return None

    summary = summarize_session(parsed)

    ts = parsed["first_ts"] or datetime.now(timezone.utc).isoformat()
    date_str = ts[:10]
    short_id = sid[:8]
    filename = f"{date_str}_{short_id}_session.md"

    sessions_dir = get_sessions_dir(project)
    out_path = sessions_dir / filename
    atomic_write(out_path, summary)

    state.setdefault("captured_sessions", {})[file_key] = {
        "mtime": mtime,
        "file": str(out_path),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)

    return out_path
