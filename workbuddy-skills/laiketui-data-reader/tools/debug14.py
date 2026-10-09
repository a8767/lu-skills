#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Set the real July 1-31 range by clicking day 1 then re-finding and clicking day 31."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.3)
ld.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));")
time.sleep(0.3)

ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
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
        "    return {x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height, cls:(e.getAttribute('class')||'').slice(0,40)};"
        "  }"
        "}"
        "return {err:'not found'};"
    )
    return ld.eval(js)

info = find_col("start", 1)
print("day1:", info)
ld._click_at(info["x"], info["y"])
time.sleep(0.6)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d14_s1.png")

info = find_col("start", 31)
print("day31:", info)
ld._click_at(info["x"], info["y"])
time.sleep(1.0)
print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d14_s2.png")
ld.close()
