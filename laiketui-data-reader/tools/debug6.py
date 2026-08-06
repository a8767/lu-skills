#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use real mouse click (ld.click) on the 自定义 tag trigger and screenshot."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
ld.eval("document.body.click();")
time.sleep(0.4)

# Selector: the last radio option (自定义) trigger span inside the main picker
expr = ("document.querySelector('.advanced-date-picker-nIYVtO "
        ".byted-radio-group > span:last-child')")
print("target expr:", expr)
info = ld.eval("var el=" + expr + "; if(!el) return null; "
               "return {tag:el.tagName, class:(el.getAttribute('class')||''), "
               "text:el.textContent.trim(), rect:el.getBoundingClientRect()};")
print("target info:", info)

r = ld.click(expr)
print("[real-click 自定义 trigger] ->", r)
time.sleep(1.2)
print("period after:", ld.period_text())

ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_custom2.png")
print("saved shot_custom2.png")
ld.close()
