#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggregate.py — 抖音来客多维度复盘聚合与报告生成引擎

支持周期:  week / month / quarter / year
支持四类数据: 统计(stats) / 对比(comparison: 环比qoq + 同比yoy) / 趋势(trend) / 目标完成度(goal)

子命令:
  period   计算某参考日期下的周期范围
  collect  把一次抓取的指标写入 canonical 记录 (data/<client>/records/<key>.json)
  rollup   从更细周期聚合出更粗周期记录 (周→月→季→年)
  review   生成某周期的完整复盘报告(.md) + 聚合数据(.csv)，含四类数据
  query    按 客户/周期类型/起止日期 灵活查询已存记录

依赖: 仅标准库 (argparse, csv, json, os, sys, datetime)。
      可选: openpyxl（仅 --xlsx 时需要，report 默认输出 md+csv）。

使用:
  python aggregate.py period --type week --ref 2026-07-14 --completed
  python aggregate.py review --client 青石峡漂流 --type month --ref 2026-07-14 \
        --data-dir data --targets config/targets.json --out reviews --trend-count 12
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta

# ---------------- 指标定义 ----------------
# 键: (中文标签, 单位, 聚合口径)
# agg: sum=可加总; derive=由分子/分母推导
METRICS = {
    "gmv": ("成交GMV", "元", "sum"),
    "verified_amount": ("核销金额", "元", "sum"),
    "refund_amount": ("退款金额", "元", "sum"),
    "coupon_sold": ("成交券数", "张", "sum"),
    "coupon_verified": ("核销券数", "张", "sum"),
    "exposure": ("线上曝光次数", "次", "sum"),
    "store_visits": ("门店页访问人数", "人", "sum"),
    "live_gmv": ("直播成交金额", "元", "sum"),
    "live_verified": ("直播核销金额", "元", "sum"),
    "live_refund": ("直播退款金额", "元", "sum"),
    "live_hours": ("直播时长", "小时", "sum"),
    "live_sessions": ("直播场次数", "场", "sum"),
    "live_exposure_users": ("直播间曝光人数", "人", "sum"),
    "video_gmv": ("视频成交金额", "元", "sum"),
    "video_views": ("视频播放量", "次", "sum"),
    "video_plant_value": ("种草价值", "元", "sum"),
    "video_coupon": ("视频成交券数", "张", "sum"),
    "search_gmv": ("搜索成交金额", "元", "sum"),
    "search_verified": ("搜索核销金额", "元", "sum"),
    "search_exposure_users": ("搜索曝光人数", "人", "sum"),
    "search_orders": ("搜索成交人数", "人", "sum"),
    "new_customers": ("新客成交数", "人", "sum"),
    "returning_customers": ("老客成交数", "人", "sum"),
    "repurchase_users": ("复购人数", "人", "sum"),
    "verify_rate": ("核销率", "%", "derive"),
    "refund_rate": ("退款率", "%", "derive"),
    "repurchase_rate": ("复购率", "%", "derive"),
}

# 率类指标推导所需分子/分母
DERIVE_FORMULA = {
    "verify_rate": ("coupon_verified", "coupon_sold"),
    "refund_rate": ("refund_amount", "gmv"),
    "repurchase_rate": ("repurchase_users", "new_customers"),
}

PERIOD_ORDER = ["week", "month", "quarter", "year"]
TYPE_LABEL = {"week": "周", "month": "月", "quarter": "季", "year": "年"}

# 趋势默认子周期数量
TREND_COUNT = {"week": 8, "month": 12, "quarter": 8, "year": 5}


# ---------------- 日期 / 周期工具 ----------------
def parse_date(s):
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {s}")


def iso_week_start(d):
    return d - timedelta(days=d.weekday())


def period_range(ptype, ref, completed=False):
    """返回该周期的范围字典。ref 可为 date/字符串。"""
    ref = parse_date(ref)
    if completed:
        if ptype == "week":
            ref = ref - timedelta(days=7)
        elif ptype == "month":
            first = ref.replace(day=1)
            ref = (first - timedelta(days=1)).replace(day=1)
        elif ptype == "quarter":
            q = (ref.month - 1) // 3
            if q == 0:
                ref = date(ref.year - 1, 10, 1)
            else:
                ref = date(ref.year, (q - 1) * 3 + 1, 1)
        elif ptype == "year":
            ref = date(ref.year - 1, 1, 1)

    if ptype == "week":
        start = iso_week_start(ref)
        end = start + timedelta(days=6)
        label = f"{start.year}-W{start.isocalendar().week:02d}"
        key = f"week/{start.isoformat()}"
    elif ptype == "month":
        start = ref.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        label = f"{start.year}-{start.month:02d}"
        key = f"month/{label}"
    elif ptype == "quarter":
        q = (ref.month - 1) // 3
        start = date(ref.year, q * 3 + 1, 1)
        if q == 3:
            end = date(ref.year, 12, 31)
        else:
            end = date(ref.year, (q + 1) * 3 + 1, day=1) - timedelta(days=1)
        label = f"{ref.year}-Q{q + 1}"
        key = f"quarter/{label}"
    elif ptype == "year":
        start = date(ref.year, 1, 1)
        end = date(ref.year, 12, 31)
        label = str(ref.year)
        key = f"year/{label}"
    else:
        raise ValueError(f"未知周期类型: {ptype}")
    return {
        "period_type": ptype,
        "period_label": label,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "key": key,
    }


def prev_period_start(ptype, start):
    """返回与 start 同粒度、紧邻的上一个周期起点。"""
    start = parse_date(start)
    if ptype == "week":
        return iso_week_start(start - timedelta(days=7))
    if ptype == "month":
        first = start.replace(day=1)
        prev = (first - timedelta(days=1)).replace(day=1)
        return prev
    if ptype == "quarter":
        q = (start.month - 1) // 3
        if q == 0:
            return date(start.year - 1, 10, 1)
        return date(start.year, (q - 1) * 3 + 1, 1)
    if ptype == "year":
        return date(start.year - 1, 1, 1)
    raise ValueError(ptype)


def coarser_key(finer_ptype, start_iso, coarser_ptype):
    """给定细周期起点，返回其所属粗周期 key。"""
    return period_range(coarser_ptype, start_iso)["key"]


def key_to_filename(key):
    return key.replace("/", "__") + ".json"


# ---------------- 记录存取 ----------------
def record_path(client, key, data_dir):
    d = os.path.join(data_dir, client, "records")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key_to_filename(key))


def load_record(client, key, data_dir):
    p = record_path(client, key, data_dir)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_record(rec, data_dir):
    p = record_path(rec["client"], rec["key"], data_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return p


# ---------------- 率类推导 ----------------
def derive_rate(key, stats):
    num_k, den_k = DERIVE_FORMULA[key]
    num = stats.get(num_k)
    den = stats.get(den_k)
    if num is None or den in (None, 0):
        return None
    return round(num / den * 100, 2)


def finalize_stats(stats):
    """对 derive 类指标若未直接提供则推导。"""
    out = dict(stats)
    for k in DERIVE_FORMULA:
        if out.get(k) is None:
            v = derive_rate(k, out)
            if v is not None:
                out[k] = v
    return out


# ---------------- 子命令实现 ----------------
def cmd_period(args):
    r = period_range(args.type, args.ref, args.completed)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"type={r['period_type']} label={r['period_label']} "
              f"start={r['period_start']} end={r['period_end']} key={r['key']}")


def cmd_collect(args):
    with open(args.stats, encoding="utf-8") as f:
        stats = json.load(f)
    if isinstance(stats, dict) and "stats" in stats:
        stats = stats["stats"]
    pr = period_range(args.type, args.ref, args.completed)
    rec = {
        "client": args.client,
        "period_type": args.type,
        "period_label": pr["period_label"],
        "period_start": pr["period_start"],
        "period_end": pr["period_end"],
        "key": pr["key"],
        "collected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source": args.source,
        "stats": finalize_stats(stats),
    }
    p = save_record(rec, args.data_dir)
    print(f"[ok] 已保存记录: {p}")


def _load_targets(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_rollup(args):
    from_t, to_t = args.frm, args.to
    if PERIOD_ORDER.index(from_t) >= PERIOD_ORDER.index(to_t):
        sys.stderr.write("[err] --frm 必须比 --to 更细 (week<month<quarter<year)\n")
        return 1
    data_dir = args.data_dir
    clients = [args.client] if args.client else [
        d for d in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, d)) and d != "."
    ]
    written = 0
    for client in clients:
        rec_dir = os.path.join(data_dir, client, "records")
        if not os.path.isdir(rec_dir):
            continue
        buckets = {}
        for fn in os.listdir(rec_dir):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(rec_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
            if rec.get("period_type") != from_t:
                continue
            ck = coarser_key(from_t, rec["period_start"], to_t)
            buckets.setdefault(ck, []).append(rec)
        for ck, recs in buckets.items():
            agg = {}
            for k, (_, _, agg_type) in METRICS.items():
                if agg_type == "sum":
                    vals = [r["stats"].get(k) for r in recs if r["stats"].get(k) is not None]
                    agg[k] = round(sum(vals), 2) if vals else None
            # derive 指标在 sum 完成后重算
            agg = finalize_stats(agg)
            pr = period_range(to_t, recs[0]["period_start"])
            new_rec = {
                "client": client,
                "period_type": to_t,
                "period_label": pr["period_label"],
                "period_start": pr["period_start"],
                "period_end": pr["period_end"],
                "key": ck,
                "collected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "rollup:" + from_t,
                "stats": agg,
            }
            save_record(new_rec, data_dir)
            written += 1
            print(f"[ok] rollup {client} {from_t}->{to_t}: {ck}")
    print(f"[done] 共写入 {written} 条聚合记录")


def cmd_review(args):
    data_dir = args.data_dir
    targets = _load_targets(args.targets)
    pr = period_range(args.type, args.ref, args.completed)
    client = args.client
    rec = load_record(client, pr["key"], data_dir)
    if rec is None:
        sys.stderr.write(f"[warn] 未找到记录 {pr['key']}，尝试从更细周期 rollup…\n")
        # 尝试从最细的已有周期聚合
        for ft in PERIOD_ORDER:
            if ft == args.type:
                continue
            if PERIOD_ORDER.index(ft) < PERIOD_ORDER.index(args.type):
                # 先把 ft 聚合到目标类型
                cmd_rollup(argparse.Namespace(frm=ft, to=args.type, client=client, data_dir=data_dir))
                rec = load_record(client, pr["key"], data_dir)
                if rec:
                    break
    if rec is None:
        sys.stderr.write(f"[err] 仍无 {pr['key']} 记录，请先 collect 更细周期数据。\n")
        return 1

    stats = finalize_stats(rec["stats"])

    # ---- 对比数据 (qoq / yoy) ----
    cur_start = rec["period_start"]
    prev_start = prev_period_start(args.type, cur_start)
    prev_rec = load_record(client, period_range(args.type, prev_start)["key"], data_dir)
    yoy_start = date(*map(int, cur_start.split("-"))).replace(
        year=date(*map(int, cur_start.split("-"))).year - 1)
    yoy_rec = load_record(client, period_range(args.type, yoy_start)["key"], data_dir)

    def delta(cur, other):
        out = {}
        for k in METRICS:
            cv = stats.get(k)
            ov = other.get(k) if other else None
            if cv is None or ov in (None, 0):
                out[k] = None
            else:
                out[k] = round((cv - ov) / ov * 100, 2)
        return out

    qoq = delta(stats, prev_rec["stats"] if prev_rec else None)
    yoy = delta(stats, yoy_rec["stats"] if yoy_rec else None)

    # ---- 趋势分析 ----
    n = args.trend_count or TREND_COUNT[args.type]
    trend_labels, trend_series = [], {k: [] for k in METRICS}
    cur = parse_date(cur_start)
    for i in range(n):
        step_start = cur
        for _ in range(i):
            step_start = prev_period_start(args.type, step_start)
        pk = period_range(args.type, step_start)["key"]
        prec = load_record(client, pk, data_dir)
        trend_labels.append(period_range(args.type, step_start)["period_label"])
        ps = finalize_stats(prec["stats"]) if prec else {}
        for k in METRICS:
            trend_series[k].append(ps.get(k))

    # ---- 目标完成度 ----
    tgt = targets.get(client, {}).get(args.type, {})
    goal = {}
    for k in METRICS:
        t = tgt.get(k)
        av = stats.get(k)
        if t is None or av is None:
            goal[k] = None
        else:
            goal[k] = round(av / t * 100, 2)

    # ---- 生成报告 ----
    md = build_markdown(client, pr, stats, qoq, yoy, prev_rec, yoy_rec,
                        trend_labels, trend_series, goal, tgt)
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    safe = pr["key"].replace("/", "__")
    md_path = os.path.join(out_dir, f"{client}__{safe}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    csv_path = os.path.join(out_dir, f"{client}__{safe}.csv")
    write_review_csv(csv_path, pr, stats, qoq, yoy, goal, tgt)
    print(f"[ok] 复盘报告: {md_path}")
    print(f"[ok] 聚合数据: {csv_path}")
    return 0


def build_markdown(client, pr, stats, qoq, yoy, prev_rec, yoy_rec,
                   trend_labels, trend_series, goal, tgt):
    L = []
    L.append(f"# {client} {TYPE_LABEL[pr['period_type']]}度复盘（{pr['period_start']} ~ {pr['period_end']}）\n")
    L.append("## 一、概览\n")
    L.append(f"- 客户：**{client}**")
    L.append(f"- 周期类型：{TYPE_LABEL[pr['period_type']]}度（{pr['period_label']}）")
    L.append(f"- 时间范围：{pr['period_start']} ~ {pr['period_end']}")
    L.append(f"- 数据来源：{prev_rec.get('source','life-data.cn') if prev_rec else 'life-data.cn'}")
    L.append("")
    L.append("## 二、统计数据（本周期核心指标）\n")
    L.append("| 指标 | 数值 | 单位 |")
    L.append("|------|------|------|")
    for k, (label, unit, _) in METRICS.items():
        v = stats.get(k)
        L.append(f"| {label} | {fmt_num(v)} | {unit} |")
    L.append("")
    L.append("## 三、对比数据\n")
    L.append("### 环比（vs 上一相邻周期）\n")
    cmp_prev = prev_rec["period_label"] if prev_rec else "（缺失）"
    L.append(f"- 对比基准：{cmp_prev}")
    L.append("| 指标 | 本期 | 上期 | 环比% |")
    L.append("|------|------|------|-------|")
    for k, (label, unit, _) in METRICS.items():
        cv = stats.get(k)
        pv = prev_rec["stats"].get(k) if prev_rec else None
        L.append(f"| {label} | {fmt_num(cv)} | {fmt_num(pv)} | {fmt_pct(qoq.get(k))} |")
    L.append("")
    L.append("### 同比（vs 去年同期）\n")
    cmp_yoy = yoy_rec["period_label"] if yoy_rec else "（缺失）"
    L.append(f"- 对比基准：{cmp_yoy}")
    L.append("| 指标 | 本期 | 去年同期 | 同比% |")
    L.append("|------|------|----------|-------|")
    for k, (label, unit, _) in METRICS.items():
        cv = stats.get(k)
        yv = yoy_rec["stats"].get(k) if yoy_rec else None
        L.append(f"| {label} | {fmt_num(cv)} | {fmt_num(yv)} | {fmt_pct(yoy.get(k))} |")
    L.append("")
    L.append("## 四、趋势分析（最近子周期走势）\n")
    L.append("| 指标 | " + " | ".join(trend_labels) + " |")
    L.append("|" + "------|" * (len(trend_labels) + 1))
    for k, (label, unit, _) in METRICS.items():
        row = " | ".join(fmt_num(v) for v in trend_series[k])
        L.append(f"| {label} | {row} |")
    L.append("")
    L.append("## 五、目标完成度\n")
    L.append("| 指标 | 实际 | 目标 | 完成率% |")
    L.append("|------|------|------|--------|")
    for k, (label, unit, _) in METRICS.items():
        av = stats.get(k)
        tv = tgt.get(k)
        L.append(f"| {label} | {fmt_num(av)} | {fmt_num(tv) if tv is not None else '未设目标'} | {fmt_pct(goal.get(k))} |")
    L.append("")
    L.append("> 本报告由 laiketui-data-reader 自动生成，数据来自生意经数据中心。")
    return "\n".join(L) + "\n"


def write_review_csv(path, pr, stats, qoq, yoy, goal, tgt):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section", "metric_key", "metric_label", "unit",
                    "value", "qoq_pct", "yoy_pct", "target", "completion_pct"])
        for k, (label, unit, _) in METRICS.items():
            w.writerow([pr["period_label"], k, label, unit,
                        stats.get(k) if stats.get(k) is not None else "",
                        qoq.get(k) if qoq.get(k) is not None else "",
                        yoy.get(k) if yoy.get(k) is not None else "",
                        tgt.get(k) if tgt.get(k) is not None else "",
                        goal.get(k) if goal.get(k) is not None else ""])


def cmd_query(args):
    data_dir = args.data_dir
    rows = []
    for client in os.listdir(data_dir):
        rec_dir = os.path.join(data_dir, client, "records")
        if not os.path.isdir(rec_dir):
            continue
        if args.client and client != args.client:
            continue
        for fn in os.listdir(rec_dir):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(rec_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
            if args.type and rec.get("period_type") != args.type:
                continue
            if args.since and rec["period_end"] < args.since:
                continue
            if args.until and rec["period_start"] > args.until:
                continue
            rows.append(rec)
    rows.sort(key=lambda r: (r["client"], r["period_start"]))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["client", "period_type", "period_label",
                        "period_start", "period_end", "key", "source"])
            for r in rows:
                w.writerow([r["client"], r["period_type"], r["period_label"],
                            r["period_start"], r["period_end"], r["key"], r.get("source")])
        print(f"[ok] 查询到 {len(rows)} 条，已写出 {args.csv}")
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))


# ---------------- 格式化工具 ----------------
def fmt_num(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return f"{v:,}"


def fmt_pct(v):
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser(description="抖音来客多维度复盘聚合引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("period", help="计算周期范围")
    p.add_argument("--type", required=True, choices=PERIOD_ORDER)
    p.add_argument("--ref", default=datetime.now().date().isoformat())
    p.add_argument("--completed", action="store_true", help="取上一完整周期")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_period)

    c = sub.add_parser("collect", help="写入一条 canonical 记录")
    c.add_argument("--client", required=True)
    c.add_argument("--type", required=True, choices=PERIOD_ORDER)
    c.add_argument("--ref", required=True)
    c.add_argument("--stats", required=True, help="stats JSON 文件(纯对象或含stats字段)")
    c.add_argument("--completed", action="store_true")
    c.add_argument("--source", default="life-data.cn")
    c.add_argument("--data-dir", default="data")
    c.set_defaults(func=cmd_collect)

    r = sub.add_parser("rollup", help="从细周期聚合为粗周期")
    r.add_argument("--frm", required=True, choices=PERIOD_ORDER)
    r.add_argument("--to", required=True, choices=PERIOD_ORDER)
    r.add_argument("--client", default=None)
    r.add_argument("--data-dir", default="data")
    r.set_defaults(func=cmd_rollup)

    rv = sub.add_parser("review", help="生成完整复盘报告(四类数据)")
    rv.add_argument("--client", required=True)
    rv.add_argument("--type", required=True, choices=PERIOD_ORDER)
    rv.add_argument("--ref", default=datetime.now().date().isoformat())
    rv.add_argument("--completed", action="store_true")
    rv.add_argument("--data-dir", default="data")
    rv.add_argument("--targets", default=None)
    rv.add_argument("--out", default="reviews")
    rv.add_argument("--trend-count", type=int, default=0)
    rv.set_defaults(func=cmd_review)

    q = sub.add_parser("query", help="灵活查询已存记录")
    q.add_argument("--client", default=None)
    q.add_argument("--type", default=None, choices=PERIOD_ORDER)
    q.add_argument("--since", default=None)
    q.add_argument("--until", default=None)
    q.add_argument("--data-dir", default="data")
    q.add_argument("--csv", default=None)
    q.set_defaults(func=cmd_query)

    args = ap.parse_args()
    rc = args.func(args)
    sys.exit(rc if isinstance(rc, int) else 0)


if __name__ == "__main__":
    main()
