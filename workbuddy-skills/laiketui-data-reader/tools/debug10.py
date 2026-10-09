#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test clicking the inner .byted-date-item div for July 1 and 31, then confirm."""
import sys, time, json
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.4)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
time.sleep(1.2)

FIND_ITEM = """
(function(args){
  var side=args.side, day=args.day;
  var p=document.querySelector('.byted-date-position-'+side);
  if(!p) return {err:'no panel'};
  var items=[].slice.call(p.querySelectorAll('.byted-date-item'));
  for(var i=0;i<items.length;i++){
    var e=items[i];
    if((e.textContent||'').trim()===String(day) &&
       (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&
       (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){
      var r=e.getBoundingClientRect();
      window.__lastDayEl=e;
      return {day:day, side:side, x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height, cls:(e.getAttribute('class')||'').slice(0,50)};
    }
  }
  return {err:'not found', day:day, side:side};
})
"""

def click_item(side, day):
    info = ld.eval("return " + FIND_ITEM + "(" + json.dumps({"side": side, "day": day}) + ")")
    print("found:", info)
    if "x" not in info:
        return False
    # Try real mouse click on the item div
    for typ in ("mousePressed", "mouseReleased"):
        ld._send("Input.dispatchMouseEvent",
                 {"type": typ, "x": info["x"], "y": info["y"],
                  "button": "left", "clickCount": 1 if typ == "mousePressed" else 0,
                  "modifiers": 0}, timeout=10)
    return True

click_item("start", 1)
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_after_1.png")
click_item("start", 31)
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_after_31.png")

# confirm via primary button
try:
    ld.click("document.querySelector('button.byted-btn-type-primary')")
except Exception as e:
    print("confirm click err:", e)
    ld.click_text("确认")
time.sleep(1.2)
print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_final.png")
ld.close()
