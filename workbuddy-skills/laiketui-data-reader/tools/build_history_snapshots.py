#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_history_snapshots.py — 林客商家数据「历史月度快照」编排器（上收至 skill）

复用 fetch_list_panel.fetch_merchants() 逐月拉取并归一化，写入：
    <history-dir>/{yyyy-MM}.json          单月快照
    <history-dir>/list.json               索引 {"periods":[...]}

本脚本只负责"循环月份 + 落盘"，取数链路全部委托给 fetch_list_panel（single source of truth）。
任何项目（personal-workbench 等）直接调用本脚本即可，无需复制取数逻辑。

用法：
    python build_history_snapshots.py --history-dir <dir> --months 2026-01..2026-08
    python build_history_snapshots.py --history-dir <dir> --months all      # 截至当月
    python build_history_snapshots.py --history-dir <dir> --months 2026-07,2026-08
"""
import argparse
import json
import os
import sys
import time
import datetime
import calendar

SKILL_TOOLS = os.path.dirname(os.path.abspath(__file__))
if SKILL_TOOLS not in sys.path:
    sys.path.insert(0, SKILL_TOOLS)
import fetch_list_panel as fpl  # noqa: E402


def parse_months(spec, today=None):
    """把 --months 解析为 ['YYYY-MM', ...]。支持 范围(2026-01..2026-08) / 列表(2026-07,2026-08) / all。"""
    today = today or datetime.date.today()
    if spec == "all":
        # 从这个 skill 首个已知月份 2026-01 到当前月
        out = []
        y, m = 2026, 1
        while (y, m) <= (today.year, today.month):
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
        return out
    if ".." in spec:
        a, b = spec.split("..", 1)
        ya, ma = map(int, a.split("-"))
        yb, mb = map(int, b.split("-"))
        out = []
        y, m = ya, ma
        while (y, m) <= (yb, mb):
            out.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
        return out
    return [x.strip() for x in spec.split(",") if x.strip()]


def month_bounds(ym):
    y, m = map(int, ym.split("-"))
    last = calendar.monthrange(y, m)[1]
    return f"{ym}-01", f"{ym}-{last:02d}"


def main(argv=None):
    p = argparse.ArgumentParser(description="林客商家数据历史月度快照生成")
    p.add_argument("--history-dir", required=True, help="历史快照目录（写 {yyyy-MM}.json + list.json）")
    p.add_argument("--months", default="all", help="月份范围：2026-01..2026-08 | 2026-07,2026-08 | all(截至当月)")
    p.add_argument("--account-id", default=fpl.DEFAULT_ACCOUNT_ID)
    p.add_argument("--ac-app", default=fpl.DEFAULT_AC_APP)
    p.add_argument("--sleep", type=float, default=0.8, help="月与月之间的间隔秒数")
    args = p.parse_args(argv)

    os.makedirs(args.history_dir, exist_ok=True)
    months = parse_months(args.months)
    if not months:
        print("[错误] 未解析到任何月份", file=sys.stderr)
        sys.exit(1)
    print(f"[计划] 将生成 {len(months)} 个月份快照：{months[0]} ~ {months[-1]}")

    import ld  # 复用 skill CDP 客户端
    inst = ld.LD(target_hint="life-partner")
    print(f"[连接] hint={inst.hint} tid={inst.tid}")

    periods = []
    for ym in months:
        start, end = month_bounds(ym)
        try:
            recs = fpl.fetch_merchants(inst, start, end, args.account_id, args.ac_app)
        except Exception as e:
            print(f"[ERR] {ym} 取数异常：{e}", file=sys.stderr)
            continue
        snap = fpl.build_month_snapshot(recs, ym, start, end)
        fn = f"{ym}.json"
        with open(os.path.join(args.history_dir, fn), "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        periods.append({"key": snap["key"], "label": snap["label"],
                        "file": fn, "count": snap["count"], "statTime": snap["statTime"]})
        print(f"[{ym}] 已写 {fn}（{snap['count']} 家）", flush=True)
        time.sleep(args.sleep)

    with open(os.path.join(args.history_dir, "list.json"), "w", encoding="utf-8") as f:
        json.dump({"periods": periods}, f, ensure_ascii=False, indent=1)
    print(f"[完成] 共写入 {len(periods)} 个月份快照 -> {args.history_dir}/list.json")
    for p_ in periods:
        print("   ", p_["file"], p_["count"], "家", p_["label"])


if __name__ == "__main__":
    main()
