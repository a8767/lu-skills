#!/usr/bin/env python3
"""Validate Workbench social insight Markdown contracts with stdlib only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SUPPORTED_TYPES = {"social-insight-report", "social-trend-report"}
VALID_STATUSES = {"complete", "partial", "needs-review"}
REQUIRED_SECTIONS = {
    "social-insight-report": {
        "样本概览",
        "一页结论",
        "评论区需求地图",
        "跨平台差异",
        "脱敏证据摘录",
        "证据边界与已排除内容",
    },
    "social-trend-report": {
        "扫描范围",
        "风向簇",
        "来源覆盖",
        "重点证据",
        "证据边界与已排除内容",
    },
}
REQUIRED_FIELDS = {
    "social-insight-report": {
        "type",
        "schema_version",
        "status",
        "title",
        "topic",
        "research_question",
        "captured_at",
        "primary_platform",
        "privacy_level",
        "sample",
    },
    "social-trend-report": {
        "type",
        "schema_version",
        "status",
        "title",
        "captured_at",
        "timezone",
        "time_window",
        "scope",
        "privacy_level",
    },
}


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("报告缺少 YAML Frontmatter。")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("Frontmatter 没有结束分隔符。")
    raw = text[4:end]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        if match:
            data[match.group(1)] = scalar(match.group(2) or "")
    return data, text[end + 5 :]


def validate(path: Path, vault: Path | None = None) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"valid": False, "errors": [f"无法读取报告：{exc}"], "warnings": []}

    try:
        frontmatter, body = parse_frontmatter(text)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": []}

    report_type = frontmatter.get("type")
    if report_type not in SUPPORTED_TYPES:
        errors.append(f"不支持的 type：{report_type or '缺失'}。")
    if frontmatter.get("schema_version") != "1":
        errors.append("schema_version 必须为 1。")
    if frontmatter.get("status") not in VALID_STATUSES:
        errors.append("status 必须为 complete、partial 或 needs-review。")
    if frontmatter.get("privacy_level") != "deidentified":
        errors.append("privacy_level 必须为 deidentified。")

    if report_type in SUPPORTED_TYPES:
        missing_fields = sorted(
            field
            for field in REQUIRED_FIELDS[report_type]
            if field not in frontmatter
        )
        if missing_fields:
            errors.append("缺少必填 Frontmatter 字段：" + "、".join(missing_fields) + "。")

        headings = set(re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
        missing_sections = sorted(REQUIRED_SECTIONS[report_type] - headings)
        if missing_sections:
            errors.append("缺少必需章节：" + "、".join(missing_sections) + "。")

    if not re.search(r"^>\s*\[!summary\]", body, flags=re.MULTILINE | re.IGNORECASE):
        errors.append("缺少 [!summary] 一句话结论。")

    if vault is not None:
        try:
            relative = path.resolve().relative_to(vault.resolve()).as_posix()
        except ValueError:
            errors.append("报告不在指定 Vault 内。")
        else:
            if not relative.startswith("10_raw/social-insights/"):
                errors.append("最终报告必须位于 10_raw/social-insights/。")

    if frontmatter.get("status") == "complete" and errors:
        warnings.append("报告标为 complete，但仍有结构错误。")

    return {
        "valid": not errors,
        "type": report_type,
        "path": str(path),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.report, args.vault)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        state = "PASS" if result["valid"] else "FAIL"
        print(f"[{state}] {result['path']}")
        for item in result["errors"]:
            print(f"ERROR: {item}")
        for item in result["warnings"]:
            print(f"WARNING: {item}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
