#!/usr/bin/env python3
"""Append reusable platform scraping lessons to platform-scraping-patterns.md.

This helper is intentionally small and append-only. It avoids rewriting the whole
reference except inserting a bullet under the selected platform section.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

PLATFORM_ALIASES = {
    "xhs": "小红书",
    "xiaohongshu": "小红书",
    "小红书": "小红书",
    "douyin": "抖音",
    "dy": "抖音",
    "抖音": "抖音",
    "weibo": "微博",
    "微博": "微博",
    "bilibili": "B站",
    "bili": "B站",
    "b站": "B站",
    "B站": "B站",
    "general": "通用",
    "common": "通用",
    "通用": "通用",
}

VALID_PLATFORMS = ["小红书", "抖音", "微博", "B站", "通用"]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_platform(value: str) -> str:
    key = value.strip()
    normalized = PLATFORM_ALIASES.get(key) or PLATFORM_ALIASES.get(key.lower())
    if not normalized:
        raise SystemExit(f"Unsupported platform: {value}. Use one of: {', '.join(VALID_PLATFORMS)}")
    return normalized


def sanitize(value: str) -> str:
    return " ".join(value.replace("\n", " ").replace("\r", " ").split()).strip()


def ensure_accumulated_sections(text: str) -> str:
    if "## Accumulated Lessons" in text:
        return text
    sections = ["", "## Accumulated Lessons", ""]
    for platform in VALID_PLATFORMS:
        sections.extend([f"### {platform}", ""])
    return text.rstrip() + "\n" + "\n".join(sections)


def append_lesson(path: Path, platform: str, bullet: str) -> bool:
    text = path.read_text(encoding="utf-8")
    text = ensure_accumulated_sections(text)
    if bullet in text:
        return False

    heading = f"### {platform}"
    idx = text.find(heading)
    if idx == -1:
        marker = "## Accumulated Lessons"
        marker_idx = text.find(marker)
        if marker_idx == -1:
            text = ensure_accumulated_sections(text)
            idx = text.find(heading)
        else:
            insert_at = marker_idx + len(marker)
            text = text[:insert_at] + f"\n\n{heading}\n" + text[insert_at:]
            idx = text.find(heading)

    next_idx = text.find("\n### ", idx + len(heading))
    insert_at = len(text) if next_idx == -1 else next_idx
    prefix = text[:insert_at].rstrip()
    suffix = text[insert_at:]
    updated = prefix + "\n" + bullet + "\n" + suffix
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Record reusable platform scraping experience")
    parser.add_argument("--platform", required=True, help="xhs/douyin/weibo/bilibili/general or Chinese platform name")
    parser.add_argument("--lesson", required=True, help="Reusable lesson learned")
    parser.add_argument("--evidence", default="", help="Observed evidence or failure context")
    parser.add_argument("--action", default="", help="Recommended next-time action")
    parser.add_argument("--source", default="manual", help="Task/site/source label")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--file", default="", help="Override target markdown file")
    args = parser.parse_args()

    platform = normalize_platform(args.platform)
    target = Path(args.file).expanduser() if args.file else skill_root() / "references" / "platform-scraping-patterns.md"
    if not target.exists():
        raise SystemExit(f"Target file not found: {target}")

    parts = [
        f"- {sanitize(args.date)} / source: {sanitize(args.source)} / lesson: {sanitize(args.lesson)}",
    ]
    if args.evidence:
        parts.append(f"evidence: {sanitize(args.evidence)}")
    if args.action:
        parts.append(f"action: {sanitize(args.action)}")
    bullet = " / ".join(parts)

    changed = append_lesson(target, platform, bullet)
    status = "appended" if changed else "duplicate-skipped"
    print(f"{status}: {target} -> {platform}: {bullet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
