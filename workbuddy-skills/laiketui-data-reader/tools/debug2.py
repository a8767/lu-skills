#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step-by-step: click calendar icon, dump full picker popup, click 自定义, dump calendar."""
import sys, time
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period before:", ld.period_text())

# Step 1: click the calendar ICON (统计周期图标)
try:
    ld.click("document.querySelector('.byted-icon-calendar')")
    print("[ok] clicked calendar icon")
except Exception as e:
    print("[err] click icon:", e)
time.sleep(1.0)

# Dump the full picker popup HTML (the popper containing a calendar/month panel)
dump = (
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var e=all[i]; var c=(e.getAttribute('class')||'');"
    "  if((c.indexOf('byted-date-picker')>=0 || c.indexOf('panel')>=0 || c.indexOf('popper')>=0)"
    "     && e.textContent.length>30 && e.textContent.indexOf('月')>=0){"
    "    return e.outerHTML.slice(0,3500);"
    "  }"
    "}"
    "return 'no-picker-popup';"
)
print("=== picker popup HTML after icon click ===")
print(ld.eval(dump))

# Step 2: click 自定义 (preset)
r = ld.click_text("自定义")
print("[click_text 自定义] ->", r)
time.sleep(1.0)

# Re-dump after 自定义
print("=== picker popup HTML after 自定义 ===")
print(ld.eval(dump))

# Look for a confirm button text
confirm_js = (
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var t=(all[i].textContent||'').trim();"
    "  if((t==='确定'||t==='确认'||t==='应用'||t==='完成') && all[i].children.length===0){"
    "    return all[i].tagName+'|'+(all[i].getAttribute('class')||'').slice(0,40)+'|'+t;"
    "  }"
    "}"
    "return 'no-confirm-btn';"
)
print("=== confirm button ===")
print(ld.eval(confirm_js))

ld.close()
