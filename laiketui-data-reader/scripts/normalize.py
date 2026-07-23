#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize.py — 抖音来客后台提取结果规整工具

输入：
  - JSON 文件：eval 得到的二维数组（list[list[str]]），或 {"headers":[...],"rows":[[...]]}
  - HTML 文件：含 <table> 的页面（从 browser-use get html --selector table 得到）
输出：
  - CSV（默认）；加 --xlsx 且环境有 openpyxl 时输出 Excel（按 store_name/日期拆分 sheet）

用法：
  python normalize.py input.json --module 团购数据 --out out/laiketui.csv
  python normalize.py input.html --module 核销分析 --xlsx --out out/laiketui.xlsx

依赖：仅标准库（csv, json, re, sys, argparse, os, datetime）。
      可选：openpyxl（仅 --xlsx 时需要）。
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser

# ---- 字段标准化映射（忽略大小写、空格、标点） ----
FIELD_MAP = {
    "商品名称": "product_name", "套餐名": "product_name", "名称": "product_name",
    "商品id": "product_id", "券id": "product_id", "id": "product_id",
    "状态": "status", "在售状态": "status",
    "售价": "price", "价格": "price", "券价": "price",
    "销量": "sold_count", "售出量": "sold_count", "售出": "sold_count",
    "收款": "amount", "实收": "amount", "金额": "amount",
    "核销数": "verified_count", "核销量": "verified_count",
    "退款数": "refund_count", "退款": "refund_count",
    "核销率": "verify_rate",
    "退款率": "refund_rate",
    "核销金额": "verified_amount",
    "待核销金额": "pending_verify_amount",
    "订单号": "order_id", "订单id": "order_id",
    "订单状态": "order_status",
    "支付金额": "pay_amount",
    "核销时间": "verified_at",
    "门店": "store_name", "门店名": "store_name",
    "达人": "talent_name", "达人昵称": "talent_name",
    "gmv": "gmv", "达人gmv": "gmv",
    "佣金": "commission",
    "结算状态": "settle_status",
    "评分": "rating", "星级": "rating",
    "评价内容": "review_text",
    "评价时间": "review_time",
    "回复状态": "reply_status",
}

NUMERIC_KEYS = {"price", "sold_count", "amount", "verified_count", "refund_count",
                "verify_rate", "refund_rate", "verified_amount", "pending_verify_amount",
                "pay_amount", "gmv", "commission", "rating"}


def norm_key(s: str) -> str:
    return re.sub(r"[\s_\-（）()：:，,.\u3000]+", "", s).lower()


def map_header(raw: str):
    key = norm_key(raw)
    return FIELD_MAP.get(key, raw.strip())


def to_number(s: str):
    if s is None:
        return ""
    s = str(s).strip()
    if s == "":
        return ""
    # 去掉 万、%、元、¥、逗号等
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return s
    val = float(m.group(0))
    if "万" in s:
        val *= 10000
    return val


# ---- HTML 表格解析 ----
class TableExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_table = 0
        self._in_tr = False
        self._in_cell = False
        self._cur_cell = []
        self._cur_row = []
        self._cur_table = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table += 1
            self._cur_table = []
        elif tag == "tr" and self._in_table > 0:
            self._in_tr = True
            self._cur_row = []
        elif tag in ("td", "th") and self._in_tr:
            self._in_cell = True
            self._cur_cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._in_table > 0:
            if self._cur_table:
                self.tables.append(self._cur_table)
            self._cur_table = []
            self._in_table -= 1
        elif tag == "tr" and self._in_tr:
            if self._cur_row:
                self._cur_table.append(self._cur_row)
            self._in_tr = False
        elif tag in ("td", "th") and self._in_cell:
            self._cur_row.append("".join(self._cur_cell).strip())
            self._in_cell = False

    def handle_data(self, data):
        if self._in_cell:
            self._cur_cell.append(data)


def parse_html_tables(path: str):
    with open(path, encoding="utf-8", errors="ignore") as f:
        html = f.read()
    p = TableExtractor()
    p.feed(html)
    return p.tables


def load_rows(path: str):
    """返回 (headers, rows)。"""
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "rows" in data:
            rows = data["rows"]
            headers = data.get("headers") or (rows[0] if rows else [])
            if headers and rows and rows[0] == headers:
                rows = rows[1:]
            return list(headers), list(rows)
        if isinstance(data, list):
            # 可能是 [header_row, ...data_rows] 或 [[...],[...]]
            if not data:
                return [], []
            if all(isinstance(c, str) for c in data[0]):
                return list(data[0]), [r for r in data[1:]]
            return [], [r for r in data]
        raise ValueError("无法识别的 JSON 结构")
    else:
        tables = parse_html_tables(path)
        if not tables:
            raise ValueError("未在 HTML 中找到 <table>")
        # 取行数最多的表
        best = max(tables, key=len)
        if not best:
            return [], []
        headers = best[0]
        rows = best[1:]
        return headers, rows


def normalize(headers, rows):
    std_headers = [map_header(h) for h in headers]
    out = []
    for r in rows:
        if len(r) != len(std_headers):
            # 补齐/截断
            r = (list(r) + [""] * len(std_headers))[:len(std_headers)]
        rec = {}
        for k, v in zip(std_headers, r):
            rec[k] = to_number(v) if k in NUMERIC_KEYS else (v.strip() if isinstance(v, str) else v)
        out.append(rec)
    return std_headers, out


def write_csv(std_headers, records, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=std_headers)
        w.writeheader()
        for rec in records:
            w.writerow(rec)
    return out_path


def write_xlsx(std_headers, records, out_path):
    try:
        from openpyxl import Workbook
    except ImportError:
        sys.stderr.write("[warn] 未安装 openpyxl，回退输出 CSV。\n")
        return write_csv(std_headers, records, out_path.rsplit(".", 1)[0] + ".csv")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    # 按 store_name 拆分 sheet（若无则汇总）
    groups = {}
    for rec in records:
        key = rec.get("store_name") or "汇总"
        groups.setdefault(key, []).append(rec)
    for name, recs in groups.items():
        ws = wb.create_sheet(title=str(name)[:31])
        ws.append(std_headers)
        for rec in recs:
            ws.append([rec.get(h, "") for h in std_headers])
    if not groups:
        ws = wb.create_sheet(title="汇总")
        ws.append(std_headers)
    wb.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="抖音来客后台提取结果规整")
    ap.add_argument("input", help="输入文件：.json（数组）或 .html（含 table）")
    ap.add_argument("--module", default="", help="模块名，仅用于日志提示")
    ap.add_argument("--out", required=True, help="输出路径（.csv 或 .xlsx）")
    ap.add_argument("--xlsx", action="store_true", help="输出 Excel（需 openpyxl）")
    args = ap.parse_args()

    headers, rows = load_rows(args.input)
    if not rows:
        sys.stderr.write("[warn] 未解析到数据行。\n")
    std_headers, records = normalize(headers, rows)

    if args.xlsx or args.out.lower().endswith(".xlsx"):
        out = write_xlsx(std_headers, records, args.out)
    else:
        out = write_csv(std_headers, records, args.out)

    print(f"[ok] 模块={args.module or '未指定'} 行数={len(records)} 字段={len(std_headers)}")
    print(f"[ok] 输出: {out}")


if __name__ == "__main__":
    main()
