#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clean test: click 自定义 preset, then locate the calendar dropdown that appears."""
import sys, time, re
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Reset: close any open popups
ld.eval("document.body.click();")
time.sleep(0.5)
ld.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));")
time.sleep(0.5)

# Click the 自定义 preset tag
r = ld.click_text("自定义")
print("[click_text 自定义] ->", r)
time.sleep(1.2)

html = ld.eval("return document.documentElement.outerHTML")
open("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/picker2.html", "w", encoding="utf-8").write(html or "")
print("html length:", len(html or ""))

# Find calendar-ish blocks: class contains calendar/month/date and big text
classes = set(re.findall(r'class="([^"]+)"', html or ""))
cal_classes = sorted(c for c in classes if any(k in c for k in
    ["calendar", "month", "date-picker", "panel-body", "cell", "day"]))
print("=== calendar-ish classes ===")
for c in cal_classes[:50]:
    print(c)

# Extract the first block containing many day numbers (1..31) -> the calendar grid
def has_days(s):
    cnt = sum(1 for n in range(1,32) if ('>'+str(n)+'<') in s or ('"'+str(n)+'"') in s)
    return cnt
# find indices of 'byted-calendar' or 'month' in classes within html
for needle in ["byted-calendar", "date-picker-dropdown", "byted-date-picker-dropdown", "month-panel", "byted-panel"]:
    i = html.find(needle)
    if i >= 0:
        print(f"\n=== found '{needle}' at {i} ===")
        snip = html[i-100: i+3000]
        t = re.sub(r'<[^>]+>', ' ', snip)
        t = re.sub(r'\s+', ' ', t)
        print(t[:800])
ld.close()
