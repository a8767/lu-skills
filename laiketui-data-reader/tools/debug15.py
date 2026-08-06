#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robust July 1-31: find cells by grid-start/grid-end classes across both panels."""
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

def find_month_boundary(day, marker):
    """Find a day cell by text and grid marker class (grid-start/grid-end/grid-in)."""
    js = (
        f"var day={day}, marker={repr(marker)};"
        "var panel=document.querySelector('.byted-date-panel');"
        "if(!panel) return {err:'no panel'};"
        "var items=[].slice.call(panel.querySelectorAll('.byted-date-item'));"
        "for(var i=0;i<items.length;i++){"
        "  var e=items[i];"
        "  var t=(e.textContent||'').trim();"
        "  var c=(e.getAttribute('class')||'');"
        "  if(t===String(day) && c.indexOf(marker)>=0){"
        "    var col=e.parentElement;"
        "    if(!col || (col.getAttribute('class')||'').indexOf('byted-date-col')<0) col=e;"
        "    var r=col.getBoundingClientRect();"
        "    return {x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height, cls:c.slice(0,50)};"
        "  }"
        "}"
        "return {err:'not found', day:day, marker:marker};"
    )
    return ld.eval(js)

info1 = find_month_boundary(1, "byted-date-grid-start")
print("July 1:", info1)
ld._click_at(info1["x"], info1["y"])
time.sleep(0.6)

info31 = find_month_boundary(31, "byted-date-grid-end")
print("July 31:", info31)
ld._click_at(info31["x"], info31["y"])
time.sleep(1.0)

print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d15.png")
ld.close()
