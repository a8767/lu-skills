#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open calendar and dump month headers + visible months."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.3)
ld.click_text("自然月")
time.sleep(1.0)
print("period after 自然月:", ld.period_text())

ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
time.sleep(1.2)

js = (
    "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
    "return views.map(function(v,i){"
    "  var h=(v.querySelector('.byted-date-nav')||{}).textContent||'';"
    "  var items=[].slice.call(v.querySelectorAll('.byted-date-item'));"
    "  var texts=items.map(function(e){return (e.textContent||'').trim()+'|'+(e.getAttribute('class')||'').slice(0,20);});"
    "  return {idx:i, header:h.trim(), cells:texts.slice(0,45)};"
    "});"
)
print(ld.eval(js))
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d18.png")
ld.close()
