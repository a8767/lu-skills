#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test 自然月 preset, then 自定义, and search HTML for calendar markers."""
import sys, time, re
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

ld.eval("document.body.click();")
time.sleep(0.4)

# Test 自然月
r = ld.click_text("自然月")
print("[click 自然月] ->", r)
time.sleep(1.0)
print("period after 自然月:", ld.period_text())

# reset to 近7日 first so 自定义 behaves predictably
ld.eval("document.body.click();")
time.sleep(0.4)

# Click 自定义
r = ld.click_text("自定义")
print("[click 自定义] ->", r)
time.sleep(1.2)

html = ld.eval("return document.documentElement.outerHTML")
markers = ["开始日期", "结束日期", "起始日期", "2026年7月", "2026年8月",
           "双月", "byted-calendar", "date-picker-dropdown", "byted-date-picker-dropdown",
           "确认", "应用", "此刻", "今日", "上个月", "上个月"]
for m in markers:
    cnt = html.count(m)
    if cnt:
        print(f"  marker '{m}': {cnt}")
# Print a context snippet around any '开始日期' / 'byted-calendar'
for needle in ["开始日期", "byted-calendar", "双月", "上个月"]:
    i = html.find(needle)
    if i >= 0:
        snip = re.sub(r'<[^>]+>', ' ', html[i-150:i+400])
        snip = re.sub(r'\s+', ' ', snip)
        print(f"\n[{needle}] {snip[:400]}")
ld.close()
