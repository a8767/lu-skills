#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract 生意经 homepage core data for July 2026."""
import sys, time, json
sys.path.insert(0, "C:/Users/Admin/.workbuddy/skills/laiketui-data-reader/tools")
from ld import LD

ld = LD()
print("period:", ld.period_text())
if "2026-07-01" not in (ld.period_text() or "") or "2026-07-31" not in (ld.period_text() or ""):
    print("Setting range to July 1-31...")
    print(ld.set_range(2026, 7, 1, 2026, 7, 31))
else:
    print("Already July range")

time.sleep(2.0)

labels = ["成交金额", "成交券数", "退款金额", "核销金额", "核销券数", "商品访问人数"]
js = (
    "var labels=[" + ",".join(json.dumps(l) for l in labels) + "];"
    "var out={};"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "  var t=(all[i].textContent||'').trim();"
    "  if(labels.indexOf(t)>=0 && !out[t]){"
    "    var p=all[i];"
    "    for(var j=0;j<6 && p;j++){"
    "      var children=p.children;"
    "      var vals=[];"
    "      for(var k=0;k<children.length;k++){"
    "        var txt=children[k].textContent.trim();"
    "        if(/[0-9\\u00a5,.]+/.test(txt) && txt.length<40){ vals.push(txt); }"
    "      }"
    "      if(vals.length>0){ out[t]=vals[0]; break; }"
    "      p=p.parentElement;"
    "    }"
    "  }"
    "}"
    "return out;"
)
print("core data:", json.dumps(ld.eval(js), ensure_ascii=False, indent=2))
print("period confirmed:", ld.period_text())
ld.close()
