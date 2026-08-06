#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open calendar, dump its DOM and locate July 1 / July 31 cells and confirm button."""
import sys, time, re
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
ld.eval("document.body.click();")
time.sleep(0.4)

# open via real click on 自定义 trigger
expr = ("document.querySelector('.advanced-date-picker-nIYVtO "
        ".byted-radio-group > span:last-child')")
ld.click(expr)
print("[opened calendar]")
time.sleep(1.0)

# Dump the calendar HTML: find the popper with month headers and day cells
html = ld.eval("return document.documentElement.outerHTML")
open("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/cal.html", "w", encoding="utf-8").write(html or "")

# Find all classes that contain calendar/month/date
classes = set(re.findall(r'class="([^"]+)"', html or ""))
cal_classes = sorted(c for c in classes if any(k in c for k in
    ["calendar", "month", "date-picker", "panel", "date-range", "date-table", "date-cell", "day"]))
print("=== calendar-ish classes ===")
for c in cal_classes[:40]:
    print(c)

# Inspect elements around "2026年7月" and "2026年8月" for 60 chars
for needle in ["2026年7月", "2026年8月"]:
    i = html.find(needle)
    if i >= 0:
        print(f"\n[{needle}] raw context:")
        print(re.sub(r'\s+',' ', html[i-80:i+250]))

# Find day cells: elements with class date-cell/calendar-cell and text 1..31
# We'll use eval to find cells in the left (July) panel
js = (
    "var out=[];"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var e=all[i]; var t=(e.textContent||'').trim();"
    "  var c=(e.getAttribute('class')||'');"
    "  if((c.indexOf('cell')>=0 || c.indexOf('day')>=0 || c.indexOf('calendar')>=0 || e.tagName==='TD')"
    "     && /^\\d{1,2}$/.test(t)){"
    "    out.push(e.tagName+'|'+c.slice(0,40)+'|'+t+'|'+(e.getAttribute('disabled')||'')+'|parent:'+(e.parentElement?e.parentElement.getAttribute('class')||'':'none'));"
    "  }"
    "}"
    "return out.slice(0,80).join('\\n');"
)
print("\n=== day cells ===")
print(ld.eval(js))

# Find confirm button
js2 = (
    "var all=[].slice.call(document.querySelectorAll('button, [role=button]'));"
    "var out=[];"
    "for(var i=0;i<all.length;i++){"
    "  var t=(all[i].textContent||'').trim();"
    "  if(t.indexOf('确定')>=0 || t.indexOf('确认')>=0 || t.indexOf('应用')>=0 || t.indexOf('完成')>=0){"
    "    out.push(all[i].tagName+'|'+t+'|'+(all[i].getAttribute('class')||'').slice(0,50));"
    "  }"
    "}"
    "return out.join('\\n');"
)
print("\n=== confirm buttons ===")
print(ld.eval(js2))

ld.close()
