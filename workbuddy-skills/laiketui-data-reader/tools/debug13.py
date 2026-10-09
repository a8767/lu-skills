#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic: close popups, open calendar, click July 1 then July 2 (same panel), confirm."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Close popups: click body, Escape, close AI report if present
ld.eval("document.body.click();")
time.sleep(0.3)
ld.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));")
time.sleep(0.3)
# try close any visible modal/popover close icon (class contains close)
ld.eval("var all=[].slice.call(document.querySelectorAll('[class*=close]')); for(var i=0;i<all.length;i++){try{all[i].click();}catch(e){}} 'closed';")
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
        "    return {x:r.x+r.width/2, y:r.y+r.height/2};"
        "  }"
        "}"
        "return {err:'not found'};"
    )
    return ld.eval(js)

info = find_col("start", 1)
print("day1:", info)
ld._click_at(info["x"], info["y"])
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d13_s1.png")

info = find_col("start", 2)
print("day2:", info)
ld._click_at(info["x"], info["y"])
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d13_s2.png")

# confirm inside calendar panel
js_btn = (
    "var panel=document.querySelector('.byted-date-panel');"
    "if(!panel) return {err:'no panel'};"
    "var btns=[].slice.call(panel.querySelectorAll('button'));"
    "for(var i=0;i<btns.length;i++){"
    "  if((btns[i].textContent||'').trim()==='确认'){"
    "    var r=btns[i].getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2};"
    "  }"
    "}"
    "return {err:'no btn'};"
)
btn = ld.eval(js_btn)
print("btn:", btn)
if "x" in btn:
    ld._click_at(btn["x"], btn["y"])
time.sleep(1.0)
print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/d13_s3.png")
ld.close()
