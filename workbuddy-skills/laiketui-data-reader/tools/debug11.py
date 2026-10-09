#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use JS .click() on the day columns directly (no real mouse dispatch)."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())
ld.eval("document.body.click();")
time.sleep(0.4)
ld.click("document.querySelector('.advanced-date-picker-nIYVtO .byted-radio-group > span:last-child')")
time.sleep(1.2)

PICK = """
var side=%r, day=%d;
var p=document.querySelector('.byted-date-position-'+side);
var items=[].slice.call(p.querySelectorAll('.byted-date-item'));
var clicked='none';
for(var i=0;i<items.length;i++){
  var e=items[i];
  if((e.textContent||'').trim()===String(day) &&
     (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&
     (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){
    var col=e.parentElement;
    if(col && (col.getAttribute('class')||'').indexOf('byted-date-col')>=0){
      col.click(); clicked='col:'+day;
    } else {
      e.click(); clicked='item:'+day;
    }
    break;
  }
}
return clicked;
"""

r1 = ld.eval(PICK % ("start", 1))
print("pick day1:", r1)
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_js1.png")
r2 = ld.eval(PICK % ("start", 31))
print("pick day31:", r2)
time.sleep(0.5)
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_js31.png")

# confirm via JS click on primary button
ld.eval("var b=document.querySelector('button.byted-btn-type-primary'); if(b){b.click();} 'confirm-clicked';")
time.sleep(1.2)
print("period after:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_jsfinal.png")
ld.close()
