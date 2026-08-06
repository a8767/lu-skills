#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect 生意经 date picker DOM so we click the right element."""
import json
import sys
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()

# 1) Find the element that contains "周期" text, dump its nearest 3 ancestors
js = (
    "var out=[];"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var t=all[i].textContent||'';"
    "  if(t.indexOf('周期')>=0 && t.length<120){"
    "    var e=all[i];"
    "    for(var k=0;k<4 && e;k++){"
    "      out.push((k)+'|'+e.tagName+'|'+(e.getAttribute('class')||'').slice(0,60)+'|'+e.textContent.slice(0,40));"
    "      e=e.parentElement;"
    "    }"
    "    break;"
    "  }"
    "}"
    "return out.join('\\n');"
)
print("=== 周期 container ancestors ===")
print(ld.eval(js))

# 2) Find all elements with an svg / calendar-ish icon & clickable
js2 = (
    "var out=[];"
    "var all=[].slice.call(document.querySelectorAll('[class*=range],[class*=date],[class*=calendar],[class*=picker]'));"
    "for(var i=0;i<all.length;i++){"
    "  var e=all[i];"
    "  out.push(e.tagName+'|'+(e.getAttribute('role')||'')+'|'+(e.getAttribute('class')||'').slice(0,70));"
    "}"
    "return out.slice(0,40).join('\\n');"
)
print("=== date/range/picker class elements ===")
print(ld.eval(js2))

# 3) Are there any buttons near the period? dump a small region of HTML around '周期'
js3 = (
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var t=all[i].textContent||'';"
    "  if(t.indexOf('周期')>=0 && t.length<120){"
    "    var p=all[i]; for(var k=0;k<3 && p;k++){p=p.parentElement;}"
    "    return p? p.outerHTML.slice(0,1500):'none';"
    "  }"
    "}"
    "return 'none';"
)
print("=== outerHTML around 周期 (3-up ancestor) ===")
print(ld.eval(js3))

ld.close()
