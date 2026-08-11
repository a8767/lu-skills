#!/usr/bin/env python3
"""Build reproducible, data-only Douyin analytics for Personal AI Workbench.

The script reads immutable official Creator Center snapshots, validates the
work-list grain, and prepares auditable account and work facts. It writes:

- analysis.json: machine-readable facts and decisions
- feedback.md: Obsidian-friendly data readout
- artifact.json: canonical Data Analytics report input
- optional local compatibility artifacts that are not published by the public
  collection entry point
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import statistics
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover - only used for the legacy fallback
    load_workbook = None


REQUIRED_COLUMNS = [
    "作品名称",
    "发布时间",
    "体裁",
    "审核状态",
    "播放量",
    "完播率",
    "5s完播率",
    "2s跳出率",
    "平均播放时长",
    "点赞量",
    "分享量",
    "评论量",
    "收藏量",
    "主页访问量",
    "粉丝增量",
]

COUNT_FIELDS = {
    "plays": "播放量",
    "likes": "点赞量",
    "shares": "分享量",
    "comments": "评论量",
    "favorites": "收藏量",
    "profile_visits": "主页访问量",
    "followers": "粉丝增量",
}

RATE_FIELDS = {
    "completion_rate": "完播率",
    "five_second_rate": "5s完播率",
    "cover_click_rate": "封面点击率",
    "two_second_bounce_rate": "2s跳出率",
}


@dataclass(frozen=True)
class SnapshotSource:
    root: Path
    work_list: Path
    captured_at: datetime


def parse_args(argv: list[str]) -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    default_vault_value = os.environ.get("PERSONAL_DASHBOARD_VAULT_ROOT")
    default_vault = Path(default_vault_value) if default_vault_value else None
    default_config = script_path.parent.parent / "assets" / "config.example.json"
    parser = argparse.ArgumentParser(description="抖音数据反馈闭环分析")
    parser.add_argument("--vault-root", type=Path, default=default_vault)
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--captured-at", help="覆盖采集时点，ISO 8601")
    parser.add_argument("--no-workflow-writeback", action="store_true")
    parser.add_argument("--no-latest-pointer", action="store_true")
    parser.add_argument("--writeback-analysis", type=Path)
    parser.add_argument(
        "--feedback-relative",
        default="30_self_media/douyin/feedback.md",
    )
    parser.add_argument("--published-source-root")
    parser.add_argument("--published-work-list")
    parser.add_argument("--published-previous")
    return parser.parse_args(argv)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_snapshot_time(root: Path, override: str | None = None) -> datetime:
    if override:
        return datetime.fromisoformat(override)
    for relative in (
        Path("02_page_snapshots/page_only_metrics.json"),
        Path("01_page_snapshots/page_only_metrics.json"),
    ):
        page_metrics = root / relative
        if not page_metrics.exists():
            continue
        try:
            capture_end = read_json(page_metrics).get("capture_window", {}).get("end")
            if capture_end:
                return datetime.fromisoformat(capture_end).replace(tzinfo=None)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    match = re.match(r"(\d{8})(?:-(\d{6}))?", root.name)
    if match:
        date_part = match.group(1)
        time_part = match.group(2) or "120000"
        return datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
    return datetime.fromtimestamp(root.stat().st_mtime)


def snapshot_root_for_work_list(work_list: Path) -> Path:
    resolved = work_list.resolve()
    for parent in resolved.parents:
        if parent.parent.name == "douyin" and parent.name != "douyin":
            return parent
    if resolved.parent.name == "sheets":
        return resolved.parents[2]
    return resolved.parent


def discover_snapshot(vault_root: Path, explicit: Path | None, captured_at: str | None) -> SnapshotSource:
    if explicit:
        work_list = resolve_work_list(explicit)
        root = snapshot_root_for_work_list(work_list)
        return SnapshotSource(root, work_list, parse_snapshot_time(root, captured_at))

    candidates: list[Path] = []
    raw_root = vault_root / "10_raw" / "douyin"
    for inventory_name in ("01_inventory", "02_inventory"):
        candidates.extend(
            raw_root.glob(f"*/{inventory_name}/sheets/*作品列表*__Sheet1.csv")
        )
    if not candidates:
        raise FileNotFoundError("没有发现已解析的官方作品列表 CSV")
    candidates.sort(
        key=lambda item: (
            parse_snapshot_time(snapshot_root_for_work_list(item)),
            item.stat().st_mtime,
        )
    )
    work_list = candidates[-1]
    root = snapshot_root_for_work_list(work_list)
    return SnapshotSource(root, work_list, parse_snapshot_time(root, captured_at))


def resolve_work_list(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        return path
    candidates = []
    for inventory_name in ("01_inventory", "02_inventory"):
        candidates.extend(path.glob(f"{inventory_name}/sheets/*作品列表*__Sheet1.csv"))
    if not candidates:
        candidates.extend(path.rglob("*作品列表*__Sheet1.csv"))
    if not candidates:
        raise FileNotFoundError(f"目录中没有作品列表 CSV：{path}")
    return sorted(candidates)[-1]


def discover_previous(
    vault_root: Path,
    current: SnapshotSource,
    explicit: Path | None,
) -> Path | None:
    if explicit:
        return resolve_work_list(explicit) if explicit.is_dir() else explicit.resolve()

    raw_root = vault_root / "10_raw" / "douyin"
    candidates: list[tuple[datetime, Path]] = []
    for inventory_name in ("01_inventory", "02_inventory"):
        for item in raw_root.glob(f"*/{inventory_name}/sheets/*作品列表*__Sheet1.csv"):
            if item.resolve() == current.work_list.resolve():
                continue
            root = snapshot_root_for_work_list(item)
            stamp = parse_snapshot_time(root)
            if stamp < current.captured_at:
                candidates.append((stamp, item))
    if candidates:
        return sorted(candidates, key=lambda pair: pair[0])[-1][1]

    legacy = raw_root / "20260707-work-list" / "作品列表.xlsx"
    return legacy if legacy.exists() else None


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "—", "None"}:
        return None
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100
        except ValueError:
            return None
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10_000
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100_000_000
        text = text[:-1]
    text = re.sub(r"[^\d.\-]", "", text)
    if not text:
        return None
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def normalize_title(value: str) -> str:
    title = value.replace("\n", " ").split("#", 1)[0].strip().lower()
    title = re.sub(r"\s+", "", title)
    title = re.sub(r"[？?！!，,。.:：；;“”\"'《》()（）/\\]", "", title)
    return title


def display_title(value: str) -> str:
    title = value.split("#", 1)[0].replace("\n", " ").strip()
    title = re.sub(r"\s+", " ", title)
    first_sentence = title.split("。", 1)[0].strip()
    if 0 < len(first_sentence) <= 70:
        return first_sentence
    return title[:70].rstrip() + ("…" if len(title) > 70 else "")


def load_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if path.suffix.lower() == ".xlsx":
        if load_workbook is None:
            raise RuntimeError("读取历史 XLSX 需要 openpyxl")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Workbook contains no default style")
            workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook[workbook.sheetnames[0]]
        values = list(sheet.iter_rows(values_only=True))
        headers = [str(value or "").strip() for value in values[0]]
        raw_rows = [dict(zip(headers, row)) for row in values[1:] if any(row)]
    else:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            raw_rows = list(reader)

    rows = []
    for raw in raw_rows:
        title_raw = str(raw.get("作品名称") or "").strip()
        published_raw = str(raw.get("发布时间") or "").strip()
        if not title_raw or not published_raw:
            continue
        try:
            published_at = datetime.fromisoformat(published_raw)
        except ValueError:
            continue
        row: dict[str, Any] = {
            "title_raw": title_raw,
            "title": display_title(title_raw),
            "title_key": normalize_title(title_raw),
            "published_at": published_at,
            "format": str(raw.get("体裁") or "").strip(),
            "status": str(raw.get("审核状态") or "").strip(),
        }
        for key, field in COUNT_FIELDS.items():
            parsed = parse_number(raw.get(field))
            row[key] = int(parsed) if parsed is not None else None
        for key, field in RATE_FIELDS.items():
            row[key] = parse_number(raw.get(field))
        row["average_watch_seconds"] = parse_number(raw.get("平均播放时长"))
        plays = row["plays"] or 0
        if plays > 0:
            row["value_action_rate"] = ((row["favorites"] or 0) + (row["shares"] or 0)) / plays
            row["interaction_rate"] = (
                (row["likes"] or 0)
                + (row["comments"] or 0)
                + (row["shares"] or 0)
                + (row["favorites"] or 0)
            ) / plays
            row["profile_visit_rate"] = (row["profile_visits"] or 0) / plays
            row["follow_rate"] = (row["followers"] or 0) / plays
        else:
            row["value_action_rate"] = None
            row["interaction_rate"] = None
            row["profile_visit_rate"] = None
            row["follow_rate"] = None
        rows.append(row)
    rows.sort(key=lambda item: item["published_at"], reverse=True)
    return rows, headers


def classify_content_line(row: dict[str, Any], config: dict[str, Any]) -> str:
    title_key = row.get("title_key", "")
    override = config.get("content_line_overrides", {}).get(title_key)
    if override:
        return override
    for prefix, content_line in config.get("content_line_prefix_overrides", {}).items():
        if title_key.startswith(prefix):
            return content_line
    title = row["title"].lower()
    for rule in config["content_lines"]:
        if any(keyword.lower() in title for keyword in rule["title_keywords"]):
            return rule["name"]
    return config["default_content_line"]


def median(rows: Iterable[dict[str, Any]], field: str) -> float | None:
    values = [row[field] for row in rows if row.get(field) is not None]
    return statistics.median(values) if values else None


def safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def pct(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value * 100:.{digits}f}%"


def num(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    if digits == 0:
        return f"{int(round(value)):,}"
    return f"{value:,.{digits}f}"


def relative_gap(value: float | None, baseline: float | None, lower_is_better: bool = False) -> float | None:
    if value is None or baseline in (None, 0):
        return None
    raw = value / baseline - 1
    return -raw if lower_is_better else raw


def validate_rows(
    rows: list[dict[str, Any]],
    headers: list[str],
    previous_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing_columns:
        errors.append(f"缺少必需字段：{', '.join(missing_columns)}")
    if not rows:
        errors.append("作品列表没有可用数据行")

    identities = [(row["title_key"], row["published_at"].isoformat()) for row in rows]
    duplicate_count = len(identities) - len(set(identities))
    if duplicate_count:
        errors.append(f"发现 {duplicate_count} 条重复作品身份")

    for row in rows:
        for field in COUNT_FIELDS:
            value = row.get(field)
            if value is not None and value < 0:
                errors.append(f"{row['title']} 的 {field} 为负数")
        for field in RATE_FIELDS:
            value = row.get(field)
            if value is not None and not 0 <= value <= 1:
                errors.append(f"{row['title']} 的 {field} 超出 0–100%")

    non_public = sum(1 for row in rows if row["status"] and row["status"] != "公开")
    if non_public:
        warnings.append(f"{non_public} 条作品不是“公开”状态；账号总计需注明范围")

    monotonic_violations: list[str] = []
    matched = 0
    if previous_rows:
        previous_map = {(row["title_key"], row["published_at"]): row for row in previous_rows}
        for row in rows:
            prior = previous_map.get((row["title_key"], row["published_at"]))
            if not prior:
                continue
            matched += 1
            for field in COUNT_FIELDS:
                if (
                    row.get(field) is not None
                    and prior.get(field) is not None
                    and row[field] < prior[field]
                ):
                    monotonic_violations.append(f"{row['title']} / {field}")
        if monotonic_violations:
            warnings.append(
                "累计字段出现下降，可能是平台口径变化或作品状态变化："
                + "、".join(monotonic_violations[:8])
            )

    return {
        "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
        "errors": errors,
        "warnings": warnings,
        "row_count": len(rows),
        "required_column_count": len(REQUIRED_COLUMNS),
        "missing_columns": missing_columns,
        "duplicate_count": duplicate_count,
        "non_public_count": non_public,
        "previous_matched_count": matched,
        "monotonic_violation_count": len(monotonic_violations),
    }


def summarize_account(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {field: sum((row.get(field) or 0) for row in rows) for field in COUNT_FIELDS}
    plays = totals["plays"]
    weighted_fields = [
        "completion_rate",
        "five_second_rate",
        "two_second_bounce_rate",
        "average_watch_seconds",
    ]
    weighted = {}
    for field in weighted_fields:
        numerator = sum(
            (row.get(field) or 0) * (row.get("plays") or 0)
            for row in rows
            if row.get(field) is not None
        )
        denominator = sum(
            (row.get("plays") or 0) for row in rows if row.get(field) is not None
        )
        weighted[field] = safe_ratio(numerator, denominator)
    return {
        "work_count": len(rows),
        **totals,
        **weighted,
        "median_plays": median(rows, "plays"),
        "value_action_rate": safe_ratio(totals["favorites"] + totals["shares"], plays),
        "profile_visit_rate": safe_ratio(totals["profile_visits"], plays),
        "follow_rate": safe_ratio(totals["followers"], plays),
    }


def summarize_content_lines(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row["content_line"] = classify_content_line(row, config)
        groups[row["content_line"]].append(row)
    total_plays = sum((row["plays"] or 0) for row in rows)
    total_favorites = sum((row["favorites"] or 0) for row in rows)
    summaries = []
    for name, group in groups.items():
        plays = sum((row["plays"] or 0) for row in group)
        favorites = sum((row["favorites"] or 0) for row in group)
        shares = sum((row["shares"] or 0) for row in group)
        profile_visits = sum((row["profile_visits"] or 0) for row in group)
        followers = sum((row["followers"] or 0) for row in group)
        summaries.append(
            {
                "content_line": name,
                "works": len(group),
                "plays": plays,
                "play_share": safe_ratio(plays, total_plays),
                "median_plays": median(group, "plays"),
                "favorites": favorites,
                "favorite_share": safe_ratio(favorites, total_favorites),
                "value_action_rate": safe_ratio(favorites + shares, plays),
                "profile_visit_rate": safe_ratio(profile_visits, plays),
                "follow_rate": safe_ratio(followers, plays),
            }
        )
    return sorted(summaries, key=lambda item: item["plays"], reverse=True)


def load_page_metrics(snapshot_root: Path) -> dict[str, Any] | None:
    candidates = [
        snapshot_root / "02_page_snapshots" / "page_only_metrics.json",
        snapshot_root / "01_page_snapshots" / "page_only_metrics.json",
    ]
    for path in candidates:
        if path.exists():
            return read_json(path)
    return None


def diagnose_latest(
    rows: list[dict[str, Any]],
    captured_at: datetime,
    config: dict[str, Any],
    page_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    focus = rows[0]
    peers = [
        row
        for row in rows[1:]
        if row["format"] == focus["format"] and (row["plays"] or 0) >= 500
    ]
    if len(peers) < 3:
        peers = [row for row in rows[1:6] if (row["plays"] or 0) >= 500]
        baseline_label = "最近 5 条已发布作品中位数"
    else:
        baseline_label = f"同体裁历史作品中位数（n={len(peers)}）"

    metrics = [
        ("two_second_retained", "2 秒留存", 1 - focus["two_second_bounce_rate"] if focus["two_second_bounce_rate"] is not None else None, 1 - median(peers, "two_second_bounce_rate") if median(peers, "two_second_bounce_rate") is not None else None),
        ("five_second_rate", "5 秒完播", focus["five_second_rate"], median(peers, "five_second_rate")),
        ("completion_rate", "整体完播", focus["completion_rate"], median(peers, "completion_rate")),
        ("value_action_rate", "收藏+分享 / 播放", focus["value_action_rate"], median(peers, "value_action_rate")),
        ("profile_visit_rate", "主页访问 / 播放", focus["profile_visit_rate"], median(peers, "profile_visit_rate")),
        ("follow_rate", "涨粉 / 播放", focus["follow_rate"], median(peers, "follow_rate")),
    ]
    comparison = [
        {
            "metric": key,
            "label": label,
            "current": current,
            "baseline": baseline,
            "relative_gap": relative_gap(current, baseline),
        }
        for key, label, current, baseline in metrics
    ]
    age_hours = max((captured_at - focus["published_at"]).total_seconds() / 3600, 0)
    mature = (
        (focus["plays"] or 0) >= config["minimum_comparison_plays"]
        and age_hours >= config["minimum_comparison_age_hours"]
    )
    page_detail = (page_metrics or {}).get("work_detail", {})
    source_mix = page_detail.get("traffic_sources") or page_detail.get("traffic_source")
    chapters = page_detail.get("chapter_click_rate") or []
    top_chapters = chapters[:2]
    search_share = None
    for key in ("traffic_sources", "flow_sources", "source_distribution"):
        values = page_detail.get(key)
        if isinstance(values, list):
            for item in values:
                if "搜索" in str(item.get("source") or item.get("name") or ""):
                    search_share = parse_number(item.get("share") or item.get("ratio"))

    confidence = "high" if mature and len(peers) >= 5 else "medium" if mature else "low"
    return {
        "title": focus["title"],
        "title_key": focus["title_key"],
        "published_at": focus["published_at"].isoformat(sep=" "),
        "age_hours": age_hours,
        "format": focus["format"],
        "content_line": focus["content_line"],
        "plays": focus["plays"],
        "baseline_label": baseline_label,
        "peer_count": len(peers),
        "mature_for_comparison": mature,
        "confidence": confidence,
        "comparison": comparison,
        "page_evidence": {
            "top_chapters": top_chapters,
            "search_share": search_share,
            "source_mix_available": source_mix is not None,
        },
    }


def compare_snapshots(
    current_rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if not previous_rows:
        return {
            "available": False,
            "matched": 0,
            "new_works": [row["title"] for row in current_rows],
            "missing_works": [],
        }
    current_map = {(row["title_key"], row["published_at"]): row for row in current_rows}
    previous_map = {(row["title_key"], row["published_at"]): row for row in previous_rows}
    matched_keys = sorted(set(current_map) & set(previous_map))
    new_keys = sorted(set(current_map) - set(previous_map))
    missing_keys = sorted(set(previous_map) - set(current_map))
    deltas = []
    for key in matched_keys:
        current = current_map[key]
        previous = previous_map[key]
        deltas.append(
            {
                "title": current["title"],
                "plays_delta": (current["plays"] or 0) - (previous["plays"] or 0),
                "favorites_delta": (current["favorites"] or 0) - (previous["favorites"] or 0),
                "followers_delta": (current["followers"] or 0) - (previous["followers"] or 0),
            }
        )
    deltas.sort(key=lambda item: item["plays_delta"], reverse=True)
    return {
        "available": True,
        "matched": len(matched_keys),
        "new_works": [current_map[key]["title"] for key in new_keys],
        "missing_works": [previous_map[key]["title"] for key in missing_keys],
        "top_growth": deltas[:5],
        "population_comparable": not new_keys and not missing_keys,
    }


def load_detail_facts(page_metrics: dict[str, Any] | None) -> dict[str, Any]:
    detail = (page_metrics or {}).get("work_detail", {})
    traffic = (
        detail.get("traffic_source_distribution")
        or detail.get("traffic_sources")
        or detail.get("flow_source")
        or []
    )
    return {
        "title": detail.get("title"),
        "work_id": detail.get("work_id"),
        "chapters": detail.get("chapter_click_rate") or [],
        "traffic_sources": traffic,
        "search_keywords": detail.get("search_keywords") or {},
        "diagnostic": detail.get("diagnostic") or {},
        "attraction": detail.get("content_attraction_page_metrics") or {},
    }


def markdown_report(analysis: dict[str, Any]) -> str:
    account = analysis["account"]
    quality = analysis["data_quality"]
    latest = analysis["latest_work"]
    lines = analysis["content_lines"]
    source = analysis["source"]
    primary_line = lines[0]

    line_rows = "\n".join(
        f"| {item['content_line']} | {item['works']} | {item['plays']:,} | "
        f"{pct(item['play_share'])} | {pct(item['favorite_share'])} | "
        f"{pct(item['value_action_rate'])} | {pct(item['follow_rate'])} |"
        for item in lines
    )
    metric_rows = "\n".join(
        f"| {item['label']} | {pct(item['current'])} | {pct(item['baseline'])} | {pct(item['relative_gap'])} |"
        for item in latest["comparison"]
    )
    top_rows = "\n".join(
        f"| {index} | {item['title']} | {item['plays']:,} | {item['favorites']:,} | {pct(item['value_action_rate'])} | {pct(item['follow_rate'])} |"
        for index, item in enumerate(analysis["top_works"], 1)
    )
    quality_notes = quality["errors"] + quality["warnings"]
    quality_text = "\n".join(f"- {note}" for note in quality_notes) or "- 必需字段、唯一性、值域和累计字段检查通过。"
    mature = latest["mature_for_comparison"]
    maturity_summary = (
        f"已达到内部比较门槛（播放 {latest['plays']:,}，发布约 {latest['age_hours']:.1f} 小时）。"
        if mature
        else (
            f"仍是早期样本（播放 {latest['plays']:,}，发布约 {latest['age_hours']:.1f} 小时）；"
            "相对差异只作数据展示。"
        )
    )

    return f"""---
type: douyin-content-feedback
status: active
created: {analysis['generated_at'][:10]}
updated: {analysis['generated_at'][:10]}
sources:
  - "{source['work_list_relative']}"
tags:
  - douyin
  - content-data
  - content-feedback
---

# {analysis['generated_at'][:10]} 抖音内容数据反馈

## Executive Summary

- **内容线分布。** “{primary_line['content_line']}”当前贡献 {pct(primary_line['play_share'])} 播放和 {pct(primary_line['favorite_share'])} 收藏。
- **最新作品。** {latest['title']}，当前 {latest['plays']:,} 播放，发布约 {latest['age_hours']:.1f} 小时。
- **比较成熟度。** {maturity_summary}
- **比较口径。** {latest['baseline_label']}；置信度 `{latest['confidence']}`。

## 内容线分布

| 内容线 | 作品 | 播放 | 播放占比 | 收藏占比 | 收藏+分享率 | 涨粉率 |
|---|---:|---:|---:|---:|---:|---:|
{line_rows}

## 最新作品与同体裁基线

比较口径：{latest['baseline_label']}。所有阈值都是账号内部诊断触发器，不是抖音平台标准。

| 诊断指标 | 本条 | 基线 | 相对基线 |
|---|---:|---:|---:|
{metric_rows}

## 当前账号事实

| 指标 | 数值 |
|---|---:|
| 当前公开作品 | {account['work_count']} |
| 累计播放 | {account['plays']:,} |
| 累计收藏 | {account['favorites']:,} |
| 收藏+分享 / 播放 | {pct(account['value_action_rate'])} |
| 主页访问 / 播放 | {pct(account['profile_visit_rate'])} |
| 涨粉 / 播放 | {pct(account['follow_rate'])} |
| 加权 5 秒完播 | {pct(account['five_second_rate'])} |
| 加权 2 秒跳出 | {pct(account['two_second_bounce_rate'])} |

## Top 作品

| 排名 | 作品 | 播放 | 收藏 | 收藏+分享率 | 涨粉率 |
|---:|---|---:|---:|---:|---:|
{top_rows}

## 数据质量与证据边界

数据质量状态：`{quality['status']}`。

{quality_text}

- 当前作品集合与旧快照不完全一致，所以账号总播放不能直接相减当增长。
- 同一轮作品管理、投稿列表和作品详情存在采集时点差，保留各自时点，不强行改成一个数。
- 主页访问与涨粉只能分别观察，不能做用户级归因。
- 章节点击是主动跳转偏好，不等于每个章节的完整留存。
- 页面每天 12 点更新，固定任务安排在 20:30 运行。
"""


def artifact_report(analysis: dict[str, Any]) -> dict[str, Any]:
    generated_at = analysis["generated_at"]
    latest = analysis["latest_work"]
    account = analysis["account"]
    source = analysis["source"]
    comparison = {item["metric"]: item for item in latest["comparison"]}
    primary_line = analysis["content_lines"][0]

    canonical_source = {
        "id": "douyin_work_list",
        "label": "抖音创作者中心作品列表官方导出",
        "path": source["work_list_relative"],
        "query": {
            "engine": "duckdb",
            "language": "sql",
            "sql": f"SELECT * FROM read_csv_auto('{source['work_list_relative']}', header = true)",
            "description": "读取当前公开作品粒度的官方累计指标，并按作品体裁、内容线和最新作品生成内部比较。",
            "executed_at": generated_at,
            "tables_used": [source["work_list_relative"]],
            "filters": ["审核状态=公开", "作品粒度", "不把不同作品集合的账号总计直接相减"],
            "metric_definitions": {
                "收藏+分享率": "(收藏量 + 分享量) / 播放量",
                "涨粉率": "粉丝增量 / 播放量",
                "2秒留存": "1 - 2s跳出率",
            },
        },
    }
    content_rows = [
        {
            "content_line": item["content_line"],
            "works": item["works"],
            "plays": item["plays"],
            "play_share": item["play_share"],
            "favorite_share": item["favorite_share"],
            "value_action_rate": item["value_action_rate"],
            "follow_rate": item["follow_rate"],
        }
        for item in analysis["content_lines"]
    ]
    diagnostic_rows = []
    selected_metrics = [
        ("two_second_retained", "2 秒留存"),
        ("five_second_rate", "5 秒完播"),
        ("completion_rate", "整体完播"),
        ("value_action_rate", "收藏+分享率"),
        ("follow_rate", "涨粉率"),
    ]
    for key, label in selected_metrics:
        item = comparison[key]
        diagnostic_rows.extend(
            [
                {
                    "metric": label,
                    "series": "最新作品",
                    "rate": item["current"],
                },
                {
                    "metric": label,
                    "series": "同体裁中位数",
                    "rate": item["baseline"],
                },
            ]
        )
    summary_rows = [
        {
            "works": account["work_count"],
            "plays": account["plays"],
            "value_action_rate": account["value_action_rate"],
            "follow_rate": account["follow_rate"],
        }
    ]
    top_rows = analysis["top_works"]
    mature = latest["mature_for_comparison"]
    maturity_summary = (
        f"最新作品 {latest['plays']:,} 播放，已达到内部比较门槛。"
        if mature
        else (
            f"最新作品仅 {latest['plays']:,} 播放、发布约 {latest['age_hours']:.1f} 小时；"
            "相对差异只作数据展示。"
        )
    )
    title = "抖音内容数据概览"
    blocks = [
        {"id": "title", "type": "markdown", "body": f"# {title}"},
        {
            "id": "executive_summary",
            "type": "markdown",
            "sourceId": "douyin_work_list",
            "body": (
                "## Executive Summary\n\n"
                f"- **内容线分布。** “{primary_line['content_line']}”贡献 "
                f"{pct(primary_line['play_share'])} 播放和 {pct(primary_line['favorite_share'])} 收藏。\n"
                f"- **最新作品成熟度。** {maturity_summary}\n"
                f"- **比较口径。** {latest['baseline_label']}；置信度 `{latest['confidence']}`。"
            ),
        },
        {
            "id": "direction_heading",
            "type": "markdown",
            "body": (
                "## 内容线播放与收藏分布\n\n"
                "图中按当前公开作品的累计播放汇总各内容线；这是分布描述，不是选题建议。"
            ),
        },
        {"id": "content_line_chart", "type": "chart", "chartId": "content_line_share", "layout": "full"},
        {
            "id": "diagnostic_heading",
            "type": "markdown",
            "body": (
                "## 最新作品与同体裁中位数\n\n"
                "下图只比较同单位的五个比率，不生成纠正动作或下一条内容建议。"
            ),
        },
        {"id": "diagnostic_chart", "type": "chart", "chartId": "latest_vs_peer", "layout": "full"},
        {
            "id": "top_heading",
            "type": "markdown",
            "body": (
                "## 当前累计播放 Top 作品\n\n"
                "Top 作品按当前官方作品列表累计播放排序，不代表未来选题顺序。"
            ),
        },
        {"id": "top_table", "type": "table", "tableId": "top_works", "layout": "full"},
        {
            "id": "caveats",
            "type": "markdown",
            "body": (
                "## Caveats and Assumptions\n\n"
                "- 当前作品集合与旧快照不完全一致，账号总计不可直接相减当增长。\n"
                "- 同一轮不同导出存在采集时点差，作品数字会随时间增长。\n"
                "- 诊断阈值是账号内部实验触发器，不是平台通用基准。\n"
                "- 章节点击代表主动跳转偏好，不等于全量观众的逐段留存。"
            ),
        },
    ]
    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "基于官方作品列表和页面限定字段生成的数据概览，不包含内容建议。",
            "generatedAt": generated_at,
            "cards": [
                {
                    "id": "account_works",
                    "description": "当前官方导出的公开作品数量。",
                    "dataset": "summary",
                    "sourceId": "douyin_work_list",
                    "metrics": [{"label": "公开作品", "field": "works", "format": "number"}],
                },
                {
                    "id": "account_plays",
                    "description": "当前公开作品累计播放，不等于本期新增播放。",
                    "dataset": "summary",
                    "sourceId": "douyin_work_list",
                    "metrics": [{"label": "累计播放", "field": "plays", "format": "number"}],
                },
                {
                    "id": "account_value",
                    "description": "当前公开作品的收藏与分享合计除以播放。",
                    "dataset": "summary",
                    "sourceId": "douyin_work_list",
                    "metrics": [{"label": "收藏+分享率", "field": "value_action_rate", "format": "percent"}],
                },
            ],
            "charts": [
                {
                    "id": "content_line_share",
                    "title": "各内容线播放占比",
                    "subtitle": f"当前 {account['work_count']} 条公开作品；占比按累计播放计算",
                    "type": "bar",
                    "dataset": "content_lines",
                    "sourceId": "douyin_work_list",
                    "encodings": {
                        "x": {"field": "content_line", "type": "nominal", "label": "内容线"},
                        "y": {"field": "play_share", "type": "quantitative", "label": "播放占比", "format": "percent"},
                    },
                    "valueFormat": "percent",
                    "layout": "full",
                },
                {
                    "id": "latest_vs_peer",
                    "title": "最新作品与同体裁中位数",
                    "subtitle": "2 秒留存、5 秒完播、整体完播、价值动作和涨粉；均为播放口径比率",
                    "type": "bar",
                    "dataset": "diagnostic",
                    "sourceId": "douyin_work_list",
                    "encodings": {
                        "x": {"field": "metric", "type": "ordinal", "label": "指标"},
                        "y": {"field": "rate", "type": "quantitative", "label": "比率", "format": "percent"},
                        "color": {"field": "series", "type": "nominal", "label": "系列"},
                    },
                    "valueFormat": "percent",
                    "layout": "full",
                },
            ],
            "tables": [
                {
                    "id": "top_works",
                    "title": "当前播放 Top 作品",
                    "subtitle": "当前官方作品列表中的前 8 条公开作品",
                    "dataset": "top_works",
                    "sourceId": "douyin_work_list",
                    "defaultSort": {"field": "plays", "direction": "desc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "title", "label": "作品", "type": "text"},
                        {"field": "content_line", "label": "内容线", "type": "text"},
                        {"field": "plays", "label": "播放", "format": "number"},
                        {"field": "favorites", "label": "收藏", "format": "number"},
                        {"field": "value_action_rate", "label": "收藏+分享率", "format": "percent"},
                        {"field": "follow_rate", "label": "涨粉率", "format": "percent"},
                    ],
                }
            ],
            "sources": [canonical_source],
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready" if analysis["data_quality"]["status"] != "failed" else "blocked",
            "datasets": {
                "summary": summary_rows,
                "content_lines": content_rows,
                "diagnostic": diagnostic_rows,
                "top_works": top_rows,
            },
            **(
                {
                    "accessIssues": [
                        {
                            "id": "data_quality_failed",
                            "dataset": "summary",
                            "message": "作品列表数据质量门禁失败，报告仅供排错。",
                        }
                    ]
                }
                if analysis["data_quality"]["status"] == "failed"
                else {}
            ),
        },
        "sources": [canonical_source],
    }


def serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    raise TypeError(f"Unsupported type: {type(value)!r}")


def write_workflow_feedback(
    vault_root: Path,
    config: dict[str, Any],
    analysis: dict[str, Any],
    report_relative: str,
) -> Path | None:
    latest = analysis["latest_work"]
    workflow_relative = config.get("workflow_map", {}).get(latest["title_key"])
    if not workflow_relative:
        return None
    path = vault_root / workflow_relative
    if not path.exists():
        return None
    start = "<!-- douyin-feedback:start -->"
    end = "<!-- douyin-feedback:end -->"
    comparison = {item["metric"]: item for item in latest["comparison"]}
    card = f"""{start}
## 自动数据反馈卡

- 数据时点：{analysis['generated_at']}
- 当前观测：约 T+{latest['age_hours'] / 24:.1f}；播放 {latest['plays']:,}
- 比较口径：{latest['baseline_label']}
- 2 秒留存：{pct(comparison['two_second_retained']['current'])}；基线 {pct(comparison['two_second_retained']['baseline'])}
- 5 秒完播：{pct(comparison['five_second_rate']['current'])}；基线 {pct(comparison['five_second_rate']['baseline'])}
- 整体完播：{pct(comparison['completion_rate']['current'])}；基线 {pct(comparison['completion_rate']['baseline'])}
- 收藏+分享率：{pct(comparison['value_action_rate']['current'])}；基线 {pct(comparison['value_action_rate']['baseline'])}
- 涨粉率：{pct(comparison['follow_rate']['current'])}；基线 {pct(comparison['follow_rate']['baseline'])}
- 完整反馈：[[{report_relative.removesuffix('.md')}]]
{end}"""
    original = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(original):
        updated = pattern.sub(card, original)
    else:
        updated = original.rstrip() + "\n\n" + card + "\n"
    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.vault_root is None:
        raise SystemExit(
            "必须提供 --vault-root 或 PERSONAL_DASHBOARD_VAULT_ROOT，不能猜测知识库路径"
        )
    vault_root = args.vault_root.expanduser().resolve()
    config = read_json(args.config.expanduser().resolve())
    if args.writeback_analysis:
        analysis = read_json(args.writeback_analysis.expanduser().resolve())
        quality = analysis["data_quality"]
        if quality["status"] == "failed":
            raise RuntimeError("数据质量失败，拒绝更新 workflow 和稳定入口")
        workflow_path = write_workflow_feedback(
            vault_root,
            config,
            analysis,
            args.feedback_relative,
        )
        latest_pointer = vault_root / "90_runs" / "data_reviews" / "douyin" / "latest-feedback.md"
        latest_pointer.write_text(
            "---\ntype: douyin-latest-feedback-pointer\nstatus: active\n"
            f"updated: {analysis['generated_at'][:10]}\n---\n\n# 最新抖音数据反馈\n\n"
            f"- 最新反馈：[[{args.feedback_relative.removesuffix('.md')}]]\n"
            "- 当前固定数据：`30_self_media/douyin/current.json`\n"
            f"- 数据质量：`{quality['status']}`\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "analysis": str(args.writeback_analysis),
                    "workflow": str(workflow_path) if workflow_path else None,
                    "latest_pointer": str(latest_pointer),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    current = discover_snapshot(vault_root, args.snapshot, args.captured_at)
    previous_path = discover_previous(vault_root, current, args.previous)
    rows, headers = load_rows(current.work_list)
    previous_rows = load_rows(previous_path)[0] if previous_path else None

    for row in rows:
        row["content_line"] = classify_content_line(row, config)
    quality = validate_rows(rows, headers, previous_rows)
    page_metrics = load_page_metrics(current.root)
    account = summarize_account(rows)
    content_lines = summarize_content_lines(rows, config)
    latest = diagnose_latest(rows, current.captured_at, config, page_metrics)
    snapshot_comparison = compare_snapshots(rows, previous_rows)
    top_works = [
        {
            "title": row["title"],
            "content_line": row["content_line"],
            "published_at": row["published_at"].isoformat(sep=" "),
            "plays": row["plays"],
            "favorites": row["favorites"],
            "value_action_rate": row["value_action_rate"],
            "follow_rate": row["follow_rate"],
        }
        for row in sorted(rows, key=lambda item: item["plays"] or 0, reverse=True)[:8]
    ]
    generated_at = current.captured_at.isoformat()
    work_list_relative = args.published_work_list or (
        current.work_list.relative_to(vault_root).as_posix()
        if current.work_list.is_relative_to(vault_root)
        else str(current.work_list)
    )
    snapshot_root_relative = args.published_source_root or (
        current.root.relative_to(vault_root).as_posix()
        if current.root.is_relative_to(vault_root)
        else str(current.root)
    )
    analysis = {
        "schema_version": 1,
        "generated_at": generated_at,
        "analysis_scope": "账号数据质量、内容线分布与最新作品相对基线",
        "source": {
            "snapshot_root": snapshot_root_relative,
            "work_list_relative": work_list_relative,
            "previous_work_list": args.published_previous or (
                previous_path.relative_to(vault_root).as_posix()
                if previous_path and previous_path.is_relative_to(vault_root)
                else str(previous_path) if previous_path else None
            ),
        },
        "data_quality": quality,
        "account": account,
        "content_lines": content_lines,
        "work_classifications": [
            {
                "published_at": row["published_at"].isoformat(sep=" "),
                "title": row["title"],
                "content_line": row.get("content_line") or "未分类",
                "content_role": "未分类",
            }
            for row in rows
        ],
        "latest_work": latest,
        "snapshot_comparison": snapshot_comparison,
        "top_works": top_works,
        "detail_facts": load_detail_facts(page_metrics),
    }

    output_dir = (
        args.output.expanduser().resolve()
        if args.output
        else vault_root
        / "90_runs"
        / "data_reviews"
        / "douyin"
        / "feedback"
        / current.captured_at.strftime("%Y%m%d-%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = output_dir / "analysis.json"
    feedback_path = output_dir / "feedback.md"
    artifact_path = output_dir / "artifact.json"
    analysis_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, default=serialize) + "\n",
        encoding="utf-8",
    )
    feedback_path.write_text(markdown_report(analysis), encoding="utf-8")
    artifact_path.write_text(
        json.dumps(artifact_report(analysis), ensure_ascii=False, indent=2, default=serialize) + "\n",
        encoding="utf-8",
    )

    relative_feedback = (
        feedback_path.relative_to(vault_root).as_posix()
        if feedback_path.is_relative_to(vault_root)
        else args.feedback_relative
    )
    if not args.no_latest_pointer and quality["status"] != "failed":
        latest_pointer = vault_root / "90_runs" / "data_reviews" / "douyin" / "latest-feedback.md"
        latest_pointer.write_text(
            "---\ntype: douyin-latest-feedback-pointer\nstatus: active\n"
            f"updated: {generated_at[:10]}\n---\n\n# 最新抖音数据反馈\n\n"
            f"- 最新反馈：[[{relative_feedback.removesuffix('.md')}]]\n"
            f"- 当前官方快照：`{snapshot_root_relative}`\n"
            f"- 数据质量：`{quality['status']}`\n",
            encoding="utf-8",
        )

    workflow_path = None
    if not args.no_workflow_writeback and quality["status"] != "failed":
        workflow_path = write_workflow_feedback(
            vault_root,
            config,
            analysis,
            relative_feedback,
        )

    result = {
        "ok": quality["status"] != "failed",
        "quality": quality["status"],
        "snapshot": str(current.root),
        "analysis": str(analysis_path),
        "feedback": str(feedback_path),
        "artifact": str(artifact_path),
        "workflow": str(workflow_path) if workflow_path else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
