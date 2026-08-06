#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Click range-container, dump full HTML to file for offline searching."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Close any open panel first
ld.eval("document.body.click();")
time.sleep(0.5)

# Click the range-container (the 周期:... text) to open the picker dropdown
try:
    ld.click("document.querySelector('[class*=range-container]')")
    print("[ok] clicked range-container")
except Exception as e:
    print("[err]", e)
time.sleep(1.2)

# Save full HTML
html = ld.eval("return document.documentElement.outerHTML")
with open("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/picker.html", "w", encoding="utf-8") as f:
    f.write(html or "")
print("html length:", len(html or ""))

# Search for date-picker dropdown classes within the HTML
import re
classes = set(re.findall(r'class="([^"]+)"', html or ""))
hits = [c for c in classes if any(k in c for k in
        ["date-picker", "calendar", "panel", "dropdown", "range", "picker", "popper"])]
print("=== candidate classes ===")
for h in sorted(hits)[:60]:
    print(h)
ld.close()
