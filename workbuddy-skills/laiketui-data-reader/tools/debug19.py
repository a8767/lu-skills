#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reliable flow: reset to 自然月 (Aug 1-4) so calendar shows July/Aug, then July 1-31 in left panel."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Reset to natural month to ensure calendar shows July/August
ld.eval("document.body.click();")
time.sleep(0.3)
# click 自然月 (4th tag)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:nth-child(4)')")
time.sleep(1.0)
print("period after 自然月:", ld.period_text())

# Open custom calendar
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
        "    return {x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height};"
        "  }"
        "}"
        "return {err:'not found'};"
    )
    return ld.eval(js)

info1 = find_col("start", 1)
print("day1:", info1)
ld._click_at(info1["x"], info1["y"])
time.sleep(0.6)

info31 = find_col("start", 31)
print("day31:", info31)
ld._click_at(info31["x"], info31["y"])
time.sleep(1.0)

print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d19.png")
ld.close()
