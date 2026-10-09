#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open the 生意经 date picker and dump the popup DOM to find 自定义 + calendar cells."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Click the range container to open the picker popup
try:
    ld.click("document.querySelector('[class*=range-container]')")
    print("clicked range-container")
except Exception as e:
    print("click err:", e)
time.sleep(1200/1000.0)

# Dump any popper / calendar that appeared containing 自定义 or calendar
js = (
    "var out=[];"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var t=all[i].textContent||'';"
    "  if((t.indexOf('自定义')>=0 || (all[i].getAttribute('class')||'').indexOf('calendar')>=0)"
    "     && t.length<200){"
    "    var e=all[i];"
    "    out.push(e.tagName+'|'+(e.getAttribute('role')||'')+'|'+(e.getAttribute('class')||'').slice(0,50)+'|'+t.slice(0,60));"
    "  }"
    "}"
    "return out.slice(0,30).join('\\n');"
)
print("=== popup elements (自定义 / calendar) ===")
print(ld.eval(js))

# Dump a chunk of HTML of the first calendar-ish popper
js2 = (
    "var all=[].slice.call(document.querySelectorAll('[class*=calendar],[class*=picker-panel],[class*=byted-popper]'));"
    "for(var i=0;i<all.length;i++){"
    "  if(all[i].textContent.indexOf('自定义')>=0 || all[i].textContent.indexOf('日')>=0){"
    "    return all[i].outerHTML.slice(0,2500);"
    "  }"
    "}"
    "return 'no-popper-found';"
)
print("=== popper outerHTML (first match) ===")
print(ld.eval(js2))

ld.close()
