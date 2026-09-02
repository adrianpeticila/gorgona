#!/usr/bin/env python3
"""
Morning Routine — Adrian M. Peticila
Rulează zilnic la 7:00 via launchd.
Output: briefing markdown + notificare macOS.
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(os.environ.get("GORGONA_BASE", Path.home() / "workspace"))
PROJECTS_DIR = BASE / "PROJECTS"
CLAUDE_MD = BASE / "CLAUDE.md"
SESSIONS_DIR = Path.home() / ".claude" / "sessions"
BRIEFINGS_DIR = BASE / "OUTPUTS/TOOLS/briefings"
BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().date()
STALE_DAYS = 7
PENDING_KEYWORDS = ["amânat", "de decis", "reminder", "pending", "TODO", "follow-up", "de făcut", "de verificat"]


# ── 1. Content due today ────────────────────────────────────────────────────

def check_content_due() -> list[str]:
    alerts = []
    today_str = TODAY.strftime("%Y-%m-%d")

    queue_files = list(PROJECTS_DIR.rglob("post_queue.md"))
    for qf in queue_files:
        project = qf.parts[-3] if len(qf.parts) >= 3 else qf.parent.name
        text = qf.read_text(encoding="utf-8")

        # găsește posturi cu data de azi care nu sunt bifate
        sections = re.split(r'\n## ', text)
        for section in sections[1:]:
            if today_str in section:
                slug_line = section.splitlines()[0].strip()
                # verifică dacă e bifat
                if "- [x]" not in section.lower() and "- [ ] postat" in section:
                    platform_match = re.search(r'\*\*(LINKEDIN|TIKTOK|X|INSTAGRAM|SUBSTACK)\*\*', section)
                    platform = platform_match.group(1) if platform_match else "?"
                    hook_match = re.search(r'\*\*Hook:\*\* (.+)', section)
                    hook = hook_match.group(1)[:60] if hook_match else slug_line
                    alerts.append(f"[{project}] {platform} due azi: {hook}")

    return alerts


# ── 2. Proiecte stale (>7 zile fără update) ────────────────────────────────

def check_stale_projects() -> list[str]:
    alerts = []
    context_files = list(PROJECTS_DIR.rglob("*CONTEXT.md"))

    for cf in context_files:
        text = cf.read_text(encoding="utf-8")
        # caută "Last updated: DD Mon YYYY" sau "YYYY-MM-DD"
        match = re.search(
            r'Last updated[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})',
            text, re.IGNORECASE
        )
        if not match:
            continue
        date_str = match.group(1).strip()
        try:
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                last_updated = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                last_updated = datetime.strptime(date_str, "%d %b %Y").date()
        except ValueError:
            continue

        days_ago = (TODAY - last_updated).days
        if days_ago >= STALE_DAYS:
            project = cf.stem.replace("_CONTEXT", "").replace("_", " ")
            alerts.append(f"{project}: {days_ago} zile fără update (last: {last_updated})")

    return alerts


# ── 3. Pending decisions din notes/ ────────────────────────────────────────

def check_pending_decisions() -> list[str]:
    found = []
    notes_dirs = list(PROJECTS_DIR.rglob("notes"))

    for notes_dir in notes_dirs:
        if not notes_dir.is_dir():
            continue
        for note_file in notes_dir.glob("*.md"):
            text = note_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("#"):
                    continue
                if any(kw.lower() in line_stripped.lower() for kw in PENDING_KEYWORDS):
                    project = note_file.parts[-3] if len(note_file.parts) >= 3 else "?"
                    snippet = line_stripped[:80]
                    found.append(f"[{project}/{note_file.name}] {snippet}")

    # deduplicare simplă
    seen = set()
    unique = []
    for item in found:
        key = item[:60]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:15]  # max 15 pentru a nu polua briefingul


# ── 4. Sesiuni incomplete ───────────────────────────────────────────────────

def check_incomplete_sessions() -> list[str]:
    alerts = []
    if not SESSIONS_DIR.exists():
        return alerts

    # ultima dată când CLAUDE.md a fost actualizat
    try:
        claude_md_text = CLAUDE_MD.read_text(encoding="utf-8")
        match = re.search(r'Last updated:\s*(\d{1,2}\s+\w+\s+\d{4})', claude_md_text)
        if match:
            last_wrap = datetime.strptime(match.group(1).strip(), "%d %b %Y").date()
        else:
            last_wrap = None
    except Exception:
        last_wrap = None

    # sesiuni din ultimele 48h
    cutoff = datetime.now() - timedelta(hours=48)
    recent_sessions = []
    for session_file in SESSIONS_DIR.glob("*.json"):
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        if mtime >= cutoff:
            size_kb = session_file.stat().st_size / 1024
            if size_kb > 10:  # sesiuni mici (< 10KB) = conversații scurte, ignoră
                recent_sessions.append((mtime.date(), size_kb, session_file.name))

    if recent_sessions and last_wrap:
        most_recent_session_date = max(s[0] for s in recent_sessions)
        if most_recent_session_date > last_wrap:
            alerts.append(
                f"CLAUDE.md last updated {last_wrap}, dar există sesiuni din {most_recent_session_date}. "
                f"Session wrap probabil omis."
            )

    return alerts


# ── Output ──────────────────────────────────────────────────────────────────

def build_briefing(content_due, stale, pending, sessions) -> str:
    lines = [
        f"# Morning Briefing — {TODAY.strftime('%d %B %Y')}",
        f"Generat: {datetime.now().strftime('%H:%M')}",
        "",
    ]

    total_items = len(content_due) + len(stale) + len(pending) + len(sessions)

    if total_items == 0:
        lines.append("✓ Totul e în regulă. Zi bună.")
        return "\n".join(lines)

    if content_due:
        lines += ["## 📅 Content due azi", ""]
        for item in content_due:
            lines.append(f"- {item}")
        lines.append("")

    if stale:
        lines += [f"## ⚠️ Proiecte fără update >{STALE_DAYS} zile", ""]
        for item in stale:
            lines.append(f"- {item}")
        lines.append("")

    if pending:
        lines += ["## 🔖 Pending decisions", ""]
        for item in pending:
            lines.append(f"- {item}")
        lines.append("")

    if sessions:
        lines += ["## 🔴 Sesiuni posibil incomplete", ""]
        for item in sessions:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def notify(title: str, message: str):
    try:
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass


def main():
    content_due = check_content_due()
    stale = check_stale_projects()
    pending = check_pending_decisions()
    sessions = check_incomplete_sessions()

    briefing = build_briefing(content_due, stale, pending, sessions)

    # salvează briefing
    output_file = BRIEFINGS_DIR / f"{TODAY}.md"
    output_file.write_text(briefing, encoding="utf-8")
    print(briefing)

    # notificare macOS
    total = len(content_due) + len(stale) + len(pending) + len(sessions)
    if total == 0:
        notify("Morning Briefing", "Totul e în regulă. Zi bună.")
    else:
        parts = []
        if content_due:
            parts.append(f"{len(content_due)} content due")
        if stale:
            parts.append(f"{len(stale)} proiecte stale")
        if pending:
            parts.append(f"{len(pending)} decizii pending")
        if sessions:
            parts.append("sesiune incompletă")
        notify("Morning Briefing", " · ".join(parts))


if __name__ == "__main__":
    main()
