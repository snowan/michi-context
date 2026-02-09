import argparse
import os
from pathlib import Path
import sys
import time

from .store import (
    get_base_dir,
    project_name_from_path,
    find_claude_session_files,
    get_state,
    register_project,
    project_name_from_key,
)
from .capture import capture_session
from .inject import format_for_hook
from .prune import prune_old_sessions
from .learn import extract_learnings, write_learnings


def cmd_capture(args):
    cwd = args.project or os.getcwd()
    project = project_name_from_path(cwd)
    register_project(cwd)
    session_files = find_claude_session_files(cwd)

    if not session_files:
        print(f"No session files found for {cwd}", file=sys.stderr)
        return 1

    if args.session_id:
        session_files = [f for f in session_files if args.session_id in f.stem]
        if not session_files:
            print(f"No session matching {args.session_id}", file=sys.stderr)
            return 1

    captured = 0
    for sf in session_files:
        result = capture_session(sf, project)
        if result:
            print(f"Captured: {result}")
            captured += 1

    if captured == 0:
        print("No new sessions to capture", file=sys.stderr)
    else:
        print(f"Captured {captured} session(s)")
    return 0


def cmd_inject(args):
    cwd = args.project or os.getcwd()
    project = project_name_from_path(cwd)
    register_project(cwd)
    output = format_for_hook(project)
    if output:
        print(output)
    return 0


def cmd_prune(args):
    max_age = args.max_age or 30
    pruned = prune_old_sessions(max_age)
    if pruned:
        for p in pruned:
            print(f"Pruned: {p}")
        print(f"Pruned {len(pruned)} session(s)")
    else:
        print("Nothing to prune")
    return 0


def cmd_learn(args):
    cwd = args.project or os.getcwd()
    project = project_name_from_path(cwd)
    learnings = extract_learnings(project)
    out = write_learnings(project, learnings)
    print(f"Learnings written to {out}")
    print(f"  Sessions analyzed: {learnings['session_count']}")
    print(f"  Files tracked: {len(learnings['frequently_modified_files'])}")
    print(f"  Error patterns: {len(learnings['error_patterns'])}")
    return 0


def cmd_daemon(args):
    interval = args.interval or 1800
    claude_projects = Path.home() / ".claude" / "projects"

    print(f"michi-context daemon started (interval={interval}s)")

    while True:
        try:
            _daemon_tick(claude_projects)
        except Exception as e:
            print(f"Daemon error: {e}", file=sys.stderr)
        time.sleep(interval)


def _daemon_tick(claude_projects):
    if not claude_projects.exists():
        return

    state = get_state()
    projects_with_new = set()

    for project_dir in claude_projects.iterdir():
        if not project_dir.is_dir():
            continue

        project = project_name_from_key(project_dir.name)
        if not project:
            continue

        for jsonl in project_dir.glob("*.jsonl"):
            mtime = jsonl.stat().st_mtime
            age = time.time() - mtime
            if age < 300:
                continue

            file_key = f"{project}:{jsonl.stem}"
            cached = state.get("captured_sessions", {}).get(file_key, {})
            if cached.get("mtime") == mtime:
                continue

            result = capture_session(jsonl, project)
            if result:
                print(f"Auto-captured: {result}")
                projects_with_new.add(project)

    for project in projects_with_new:
        try:
            learnings = extract_learnings(project)
            write_learnings(project, learnings)
        except Exception as e:
            print(f"Learn error for {project}: {e}", file=sys.stderr)

    pruned = prune_old_sessions()
    if pruned:
        print(f"Pruned {len(pruned)} old session(s)")


def cmd_status(args):
    base = get_base_dir()
    sessions_root = base / "sessions"
    learnings_dir = base / "learnings"

    session_count = 0
    total_size = 0
    projects = set()

    if sessions_root.exists():
        for f in sessions_root.rglob("*_session.md"):
            session_count += 1
            total_size += f.stat().st_size
            projects.add(f.parent.name)

    learning_count = 0
    if learnings_dir.exists():
        learning_count = len(list(learnings_dir.glob("*.md")))

    state = get_state()
    tracked = len(state.get("captured_sessions", {}))

    print(f"michi-context status")
    print(f"  Base dir:     {base}")
    print(f"  Projects:     {len(projects)}")
    print(f"  Sessions:     {session_count}")
    print(f"  Learnings:    {learning_count}")
    print(f"  Tracked:      {tracked}")
    print(f"  Disk usage:   {total_size / 1024:.1f} KB")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="michi-context",
        description="Session memory for Claude Code",
    )
    sub = parser.add_subparsers(dest="command")

    p_capture = sub.add_parser("capture", help="Capture Claude Code sessions")
    p_capture.add_argument("--session-id", help="Capture specific session UUID")
    p_capture.add_argument("--project", help="Project path (default: cwd)")

    p_inject = sub.add_parser("inject", help="Output context JSON for Claude Code hook")
    p_inject.add_argument("--project", help="Project path (default: cwd)")

    p_prune = sub.add_parser("prune", help="Remove old session files")
    p_prune.add_argument("--max-age", type=int, help="Max age in days (default: 30)")

    p_learn = sub.add_parser("learn", help="Extract learnings from sessions")
    p_learn.add_argument("--project", help="Project path (default: cwd)")

    p_daemon = sub.add_parser("daemon", help="Run background capture/learn/prune loop")
    p_daemon.add_argument("--interval", type=int, help="Seconds between runs (default: 1800)")

    sub.add_parser("status", help="Show stats")

    args = parser.parse_args()

    commands = {
        "capture": cmd_capture,
        "inject": cmd_inject,
        "prune": cmd_prune,
        "learn": cmd_learn,
        "daemon": cmd_daemon,
        "status": cmd_status,
    }

    if args.command in commands:
        sys.exit(commands[args.command](args) or 0)
    else:
        parser.print_help()
        sys.exit(1)
