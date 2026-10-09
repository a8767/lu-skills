#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find the July panel by its header text, then select July 1 and July 31 inside it."""
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

def find_panel_and_day(day):
    js = (
        f"var targetDay={day};"
        "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
        "for(var v=0;v<views.length;v++){"
        "  var view=views[v];"
        "  var header=(view.querySelector('.byted-date-nav')||{}).textContent||'';"
        "  if(header.indexOf('2026年7月')>=0 || header.indexOf('7月')>=0){"
        "    var items=[].slice.call(view.querySelectorAll('.byted-date-item'));"
        "    for(var i=0;i<items.length;i++){"
        "      var e=items[i];"
        "      if((e.textContent||'').trim()===String(targetDay) &&"
        "         (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&"
        "         (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){"
        "        var col=e.parentElement;"
        "        if(!col || (col.getAttribute('class')||'').indexOf('byted-date-col')<0) col=e;"
        "        var r=col.getBoundingClientRect();"
        "        return {panel:v, x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height, cls:(e.getAttribute('class')||'').slice(0,40)};"
        "      }"
        "    }"
        "  }"
        "}"
        "return {err:'not found', day:targetDay};"
    )
    return ld.eval(js)

info1 = find_panel_and_day(1)
print("July 1:", info1)
ld._click_at(info1["x"], info1["y"])
time.sleep(0.6)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d16_s1.png")

info31 = find_panel_and_day(31)
print("July 31:", info31)
ld._click_at(info31["x"], info31["y"])
time.sleep(1.0)

print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d16_s2.png")
ld.close()
