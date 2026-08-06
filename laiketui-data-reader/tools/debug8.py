#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full test: set range to 2026-07-01 ~ 2026-07-31 via the calendar popup."""
import sys, time, json
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Make sure no stray popups, then open custom calendar
ld.eval("document.body.click();")
time.sleep(0.4)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
print("[opened calendar]")
time.sleep(1.0)

# JS helper: find an active day cell within a panel side (start/end)
# returns a plain object with enough info to click
FIND_DAY = """
(function(args){
  var side=args.side, day=args.day;
  var panel=document.querySelector('.byted-date-position-'+side);
  if(!panel) return {err:'no panel '+side};
  var items=[].slice.call(panel.querySelectorAll('.byted-date-item'));
  var candidates=[];
  for(var i=0;i<items.length;i++){
    var e=items[i];
    var t=(e.textContent||'').trim();
    var c=(e.getAttribute('class')||'');
    if(t===String(day) && c.indexOf('byted-date-disabled')<0){
      candidates.push(e);
    }
  }
  if(candidates.length===0) return {err:'day not found', day:day, side:side};
  var el=candidates[0];
  // click target: prefer the parent byted-date-col if item rect is tiny
  var target=el, p=el.parentElement;
  if(p && (p.getAttribute('class')||'').indexOf('byted-date-col')>=0) target=p;
  var r=target.getBoundingClientRect();
  return {
    day:day, side:side,
    tag:target.tagName, cls:(target.getAttribute('class')||'').slice(0,40),
    x: r.x+r.width/2, y: r.y+r.height/2, width:r.width, height:r.height
  };
})
"""

def click_day(side, day):
    info = ld.eval("return " + FIND_DAY + "(" + json.dumps({"side": side, "day": day}) + ")")
    print(f"  cell {day} ({side}):", info)
    if info.get("x") is None:
        raise SystemExit(f"cannot locate day {day} on {side}")
    # dispatch real mouse events at the returned coordinates
    for typ in ("mousePressed", "mouseReleased"):
        ld._send("Input.dispatchMouseEvent",
                 {"type": typ, "x": info["x"], "y": info["y"],
                  "button": "left", "clickCount": 1 if typ == "mousePressed" else 0,
                  "modifiers": 0}, timeout=10)
    return info

click_day("start", 1)
time.sleep(0.6)
click_day("start", 31)
time.sleep(0.6)

# Click confirm
ld.click("document.querySelector('button.byted-btn-type-primary')")
print("[clicked confirm]")
time.sleep(1.2)
print("period after:", ld.period_text())
ld.close()
