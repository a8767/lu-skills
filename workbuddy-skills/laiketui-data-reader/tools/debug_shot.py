#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Click 自定义 then screenshot for visual inspection."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
ld.eval("document.body.click();")
time.sleep(0.4)
r = ld.click_text("自定义")
print("[click 自定义] ->", r)
time.sleep(1.2)
print("period:", ld.period_text())
ld.screenshot("C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools/shot_custom.png")
print("saved shot_custom.png")
ld.close()
