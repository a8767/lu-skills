#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug version: open calendar, verify panel exists, list day cells."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.4)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
print("[clicked 自定义 trigger]")
time.sleep(1.5)

# Check if calendar panel exists
js = (
    "var p=document.querySelector('.byted-date-position-start');"
    "if(!p) return {err:'no position-start'};"
    "var items=[].slice.call(p.querySelectorAll('.byted-date-item'));"
    "return {panelTag:p.tagName, panelClass:(p.getAttribute('class')||''), itemCount:items.length, "
    "       texts:items.map(function(e){var t=e.textContent.trim();var c=e.getAttribute('class')||'';"
    "                                  return t+'|'+(c.indexOf('disabled')>=0?'dis':'act')+'|'+(e.parentElement?e.parentElement.getAttribute('class')||'':'none');})};"
)
print(ld.eval(js))
ld.close()
