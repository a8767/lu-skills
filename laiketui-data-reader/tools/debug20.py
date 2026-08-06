#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-click day 1, then JS .click() on the day 31 item div."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.3)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:nth-child(4)')")
time.sleep(1.0)

ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
time.sleep(1.2)

def find_item(side, day):
    js = (
        f"var side={repr(side)}, day={day};"
        "var p=document.querySelector('.byted-date-position-'+side);"
        "var items=[].slice.call(p.querySelectorAll('.byted-date-item'));"
        "for(var i=0;i<items.length;i++){"
        "  var e=items[i];"
        "  if((e.textContent||'').trim()===String(day) &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){"
        "    var col=e.parentElement;"
        "    if(!col || (col.getAttribute('class')||'').indexOf('byted-date-col')<0) col=e;"
        "    var r=col.getBoundingClientRect();"
        "    return {item:'window.__day'+day+'=document.querySelectorAll(\".byted-date-item\")['+i+']', x:r.x+r.width/2, y:r.y+r.height/2};"
        "  }"
        "}"
        "return {err:'not found'};"
    )
    return ld.eval(js)

info1 = find_item("start", 1)
print("day1:", info1)
ld._click_at(info1["x"], info1["y"])
time.sleep(0.6)

info31 = find_item("start", 31)
print("day31:", info31)
# Use JS click on the item div itself
ld.eval("var p=document.querySelector('.byted-date-position-start');"
        "var items=[].slice.call(p.querySelectorAll('.byted-date-item'));"
        "for(var i=0;i<items.length;i++){"
        "  var e=items[i];"
        "  if((e.textContent||'').trim()==='31' &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&"
        "     (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){"
        "    e.click(); break;"
        "  }"
        "} 'clicked31';")
time.sleep(1.0)

print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d20.png")
ld.close()
