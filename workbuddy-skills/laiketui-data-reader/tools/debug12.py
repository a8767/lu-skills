#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robust real-mouse flow: re-find cells after each click, confirm, verify."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.4)

# open custom calendar
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
print("[opened]")
time.sleep(1.2)

def find_col(side, day):
    js = (
        f"var side={repr(side)}, day={day};"
        "var p=document.querySelector('.byted-date-position-'+side);"
        "if(!p) return {err:'no panel'};"
        "var items=[].slice.call(p.querySelectorAll('.byted-date-item'));"
        "for(var i=0;i<items.length;i++){"
        "  var e=items[i];"
        "  if((e.textContent||'').trim()===String(day) &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){"
        "    var col=e.parentElement;"
        "    if(!col || (col.getAttribute('class')||'').indexOf('byted-date-col')<0) col=e;"
        "    var r=col.getBoundingClientRect();"
        "    return {x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height};"
        "  }"
        "}"
        "return {err:'not found'};"
    )
    return ld.eval(js)

# Step 1: click day 1
info = find_col("start", 1)
print("day1:", info)
ld._click_at(info["x"], info["y"])
time.sleep(0.6)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/s1.png")

# Step 2: re-find and click day 31
info = find_col("start", 31)
print("day31:", info)
ld._click_at(info["x"], info["y"])
time.sleep(0.6)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/s2.png")

# Step 3: find confirm button inside calendar panel
js_btn = (
    "var panel=document.querySelector('.byted-date-panel');"
    "if(!panel) return {err:'no panel'};"
    "var btns=[].slice.call(panel.querySelectorAll('button'));"
    "for(var i=0;i<btns.length;i++){"
    "  var t=(btns[i].textContent||'').trim();"
    "  if(t==='确认'||t==='确定'){"
    "    var r=btns[i].getBoundingClientRect();"
    "    return {x:r.x+r.width/2, y:r.y+r.height/2, text:t};"
    "  }"
    "}"
    "return {err:'no confirm btn'};"
)
btn = ld.eval(js_btn)
print("confirm btn:", btn)
if "x" in btn:
    ld._click_at(btn["x"], btn["y"])
    print("[confirmed]")
time.sleep(1.2)
print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/s3.png")
ld.close()
