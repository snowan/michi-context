from collections import Counter
from pathlib import Path
import re

from .store import get_sessions_dir, get_learnings_dir, atomic_write

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def extract_learnings(project: str) -> dict:
    sessions_dir = get_sessions_dir(project)
    session_files = sorted(sessions_dir.glob("*_session.md"))

    file_counts = Counter()
    error_patterns = Counter()
    all_prompts = []

    for sf in session_files:
        content = sf.read_text()

        fm_match = FRONTMATTER_RE.match(content)
        if fm_match:
            fm = fm_match.group(1)
            files_line = re.search(r"files_modified:\s*\[(.+?)\]", fm)
            if files_line:
                for f in files_line.group(1).split(","):
                    file_counts[f.strip()] += 1

        section = None
        for line in content.split("\n"):
            if line.startswith("## "):
                section = line[3:].strip()
                continue

            if section == "Errors" and line.startswith("- ") and "(none)" not in line:
                error_patterns[line[2:].strip()[:100]] += 1
            elif section == "User Prompts" and re.match(r"\d+\.\s", line):
                prompt_text = re.sub(r"^\d+\.\s*", "", line).strip()
                if prompt_text:
                    all_prompts.append(prompt_text)

    return {
        "session_count": len(session_files),
        "frequently_modified_files": file_counts.most_common(10),
        "error_patterns": error_patterns.most_common(10),
        "recent_prompts": all_prompts[-20:],
    }


def write_learnings(project: str, learnings: dict) -> Path:
    learnings_dir = get_learnings_dir()
    out_path = learnings_dir / f"{project}.md"

    lines = [f"# Learnings: {project}\n"]
    lines.append(f"Sessions analyzed: {learnings['session_count']}\n")

    if learnings["frequently_modified_files"]:
        lines.append("## Frequently Modified Files")
        for fp, count in learnings["frequently_modified_files"]:
            lines.append(f"- {fp} ({count}x)")
        lines.append("")

    if learnings["error_patterns"]:
        lines.append("## Common Errors")
        for err, count in learnings["error_patterns"]:
            lines.append(f"- [{count}x] {err}")
        lines.append("")

    if learnings["recent_prompts"]:
        lines.append("## Recent Work")
        for prompt in learnings["recent_prompts"][-10:]:
            lines.append(f"- {prompt[:120]}")
        lines.append("")

    atomic_write(out_path, "\n".join(lines))
    return out_path
