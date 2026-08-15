#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""life_data.py - 抖音来客/生意经 生意经数据中心 操作封装（CDP 直连）
依赖: websocket-client。目标页 target_id 通过 /json 自动定位（urlhint=life-data）。
提供: eval / real_click / screenshot / set_range(自定义日期) / switch_module(切顶部标签)。
"""
import json
import time
import base64
import urllib.request
import websocket

DEBUG_PORT = 9223
DEFAULT_TARGET_HINT = "life-data"
# 兼容旧名（保留避免外部脚本误引用）
TARGET_HINT = DEFAULT_TARGET_HINT

# 按叶子文本点击其最近的可点击祖先（BUTTON/role=button/clickable class）
JS_CLICK_TEXT = (
    "(function(txt){"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "for(var i=0;i<all.length;i++){"
    "var e=all[i];"
    "if(e.children.length===0 && e.textContent.trim()===txt){"
    "var el=e;"
    "for(var j=0;j<8 && el;j++){el=el.parentElement;"
    "if(el && (el.tagName==='BUTTON' || el.getAttribute('role')==='button' || (el.getAttribute('class')||'').indexOf('clickable')>=0)){el.click();return 'clicked';}}"
    "e.click();return 'leaf';}}"
    "return 'notfound:'+txt;})"
)

# 在双月日历中按 月份文本 + 日号 选中起止两日
JS_PICK_DAY = (
    "(function(monthLabels, dayNums){"
    "var all=[].slice.call(document.querySelectorAll('*'));"
    "function cell(txt,monthTxt){"
    "for(var i=0;i<all.length;i++){var e=all[i];"
    "if(e.children.length===0 && e.textContent.trim()===String(txt)){"
    "var p=e,ok=false;"
    "for(var j=0;j<8 && p;j++){if(p.textContent.indexOf(monthTxt)>=0){ok=true;break;}p=p.parentElement;}"
    "if(ok) return e;}}"
    "return null;}"
    "var s=cell(dayNums[0],monthLabels[0]), e=cell(dayNums[1],monthLabels[1]);"
    "if(s&&e){s.click();e.click();return 'picked';}"
    "return 's='+(!!s)+' e='+(!!e);})"
)


def _http_json(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}{path}", timeout=10) as r:
        return json.loads(r.read().decode())


def find_target_id(target_hint=None):
    """Locate a page-type CDP target whose URL/title contains target_hint.

    Args:
        target_hint: substring to match (e.g. 'life-data' for 生意经,
                     'life-partner' for 抖音林客). Falls back to DEFAULT_TARGET_HINT.
    """
    hint = target_hint or DEFAULT_TARGET_HINT
    for t in _http_json("/json"):
        if t.get("type") == "page" and hint in (t.get("url") or ""):
            return t.get("id"), hint
    # 没找到时，把 hint 写进报错，提示用户去对应域登录
    raise SystemExit(
        f"CDP target not found for hint={hint!r} (not logged in or wrong tab?)")


class LD:
    def __init__(self, target_id=None, target_hint=None):
        if target_id is None:
            target_id, hint = find_target_id(target_hint)
            self.hint = hint
        else:
            self.hint = target_hint or DEFAULT_TARGET_HINT
        self.tid = target_id
        self.ws = websocket.create_connection(
            f"ws://127.0.0.1:{DEBUG_PORT}/devtools/page/{self.tid}", timeout=40)
        self._id = 0
        self._send("Runtime.enable", timeout=5)
        try:
            self._send("Page.enable", timeout=5)
        except Exception:
            pass

    def _send(self, method, params=None, timeout=30):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = json.loads(self.ws.recv())
            if r.get("id") == self._id:
                if "error" in r:
                    raise RuntimeError(f"CDP err {r['error']}")
                return r.get("result")
        raise TimeoutError("cdp timeout")

    def eval(self, expr, timeout=20):
        res = self._send("Runtime.evaluate",
                         {"expression": f"(function(){{ {expr} }})()",
                          "returnByValue": True, "awaitPromise": True}, timeout=timeout)
        if res.get("exceptionDetails"):
            ed = res["exceptionDetails"]
            raise RuntimeError(f"JS: {ed.get('text')} {ed.get('exception',{}).get('description')}")
        r = res.get("result", {})
        if not isinstance(r, dict):
            import sys; print("RAW_RESULT_NON_DICT:", res, file=sys.stderr)
        if "value" not in r and "description" not in r:
            import sys; print("RAW_RESULT:", res, file=sys.stderr)
        return r.get("value") if "value" in r else r.get("description")

    def click_text(self, txt):
        # IMPORTANT: must `return` the IIFE value, otherwise eval's
        # (function(){ ... })() wrapper discards it and we get None.
        r = self.eval("return " + JS_CLICK_TEXT + "(" + json.dumps(txt) + ")")
        return r if isinstance(r, str) else "none"

    def _rect(self, expr):
        return self.eval(
            f"var el={expr}; if(!el) return null; var r=el.getBoundingClientRect();"
            f"return {{x:r.x+r.width/2,y:r.y+r.height/2}};")

    def click(self, expr, real=True):
        rect = self._rect(expr)
        if not rect:
            raise SystemExit(f"click target not found: {expr}")
        if not real:
            return self.eval(f"var el={expr}; if(el){{el.click();return 'ok';}} return 'none';")
        for typ in ("mousePressed", "mouseReleased"):
            self._send("Input.dispatchMouseEvent",
                       {"type": typ, "x": rect["x"], "y": rect["y"],
                        "button": "left", "clickCount": 1,
                        "modifiers": 0}, timeout=10)
        return "real-clicked"

    def fill(self, expr, text):
        self.eval(f"var el={expr}; if(el){{el.focus();"
                  f"if(el.select){{try{{el.select();}}catch(e){{}}}}"
                  f"if(el.setSelectionRange){{try{{el.setSelectionRange(0,el.value.length);}}catch(e){{}}}}}}")
        time.sleep(0.2)
        self._send("Input.insertText", {"text": text}, timeout=10)
        return "filled"

    def wait(self, ms):
        time.sleep(ms / 1000.0)

    def text(self, sel="body"):
        return self.eval(f"var el=document.querySelector({json.dumps(sel)}); return el?el.innerText:null;")

    def screenshot(self, path):
        res = self._send("Page.captureScreenshot", {"format": "png"}, timeout=40)
        open(path, "wb").write(base64.b64decode(res["data"]))
        return path

    def period_text(self):
        return self.eval(
            "var els=[].slice.call(document.querySelectorAll('*'));"
            "for(var i=0;i<els.length;i++){"
            "var t=els[i].textContent||'';"
            "var m=t.match(/周期[:：]\\s*(\\d{4}[-/年.\\s]*\\d{1,2}[-/月.\\s]*\\d{1,2})\\s*[~～-]\\s*(\\d{4}[-/年.\\s]*\\d{1,2}[-/月.\\s]*\\d{1,2})/);"
            "if(m) return m[0];}"
            "return null;")

    def _click_at(self, x, y):
        # Move cursor first so the element receives a real hover/enter
        self._send("Input.dispatchMouseEvent",
                   {"type": "mouseMoved", "x": x, "y": y, "modifiers": 0}, timeout=10)
        for typ in ("mousePressed", "mouseReleased"):
            self._send("Input.dispatchMouseEvent",
                       {"type": typ, "x": x, "y": y,
                        "button": "left", "clickCount": 1,
                        "modifiers": 0}, timeout=10)

    def _find_month_day(self, month_label, day):
        """Return the clickable column for a day inside the panel with the given month header."""
        js = (
            f"var monthLabel={repr(month_label)}, targetDay={day};"
            "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
            "for(var v=0;v<views.length;v++){"
            "  var view=views[v];"
            "  var header=(view.querySelector('.byted-date-nav')||{}).textContent||'';"
            "  if(header.replace(/\\s+/g,'').indexOf(monthLabel.replace(/\\s+/g,''))>=0){"
            "    var items=[].slice.call(view.querySelectorAll('.byted-date-item'));"
            "    for(var i=0;i<items.length;i++){"
            "      var e=items[i];"
            "      if((e.textContent||'').trim()===String(targetDay) &&"
            "         (e.getAttribute('class')||'').indexOf('byted-date-grid-next')<0 &&"
            "         (e.getAttribute('class')||'').indexOf('byted-date-grid-prev')<0){"
            "        var col=e.parentElement;"
            "        if(!col || (col.getAttribute('class')||'').indexOf('byted-date-col')<0) col=e;"
            "        var r=col.getBoundingClientRect();"
            "        return {panel:v, idx:i, x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height};"
            "      }"
            "    }"
            "  }"
            "}"
            "return {err:'not found'};"
        )
        return self.eval(js)

    def _click_day_item(self, panel_idx, item_idx):
        """Use JS .click() on a specific .byted-date-item (more reliable than real mouse for some cells)."""
        js = (
            f"var panelIdx={panel_idx}, itemIdx={item_idx};"
            "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
            "var view=views[panelIdx];"
            "if(!view) return {err:'no view'};"
            "var items=[].slice.call(view.querySelectorAll('.byted-date-item'));"
            "var e=items[itemIdx];"
            "if(e){ e.click(); return {ok:true, text:(e.textContent||'').trim()}; }"
            "return {err:'no item'};"
        )
        return self.eval(js)

    def _open_input_picker(self):
        """Open the calendar of an input-based (byted-input) range picker,
        e.g. the 流量/人群 modules whose date range is a readonly <input>.
        Selects the first readonly range <input> inside a byted-input wrapper
        (robust to different prefix labels like 统计周期/时间范围)."""
        sel = (
            "(function(){"
            "var labels=[].slice.call(document.querySelectorAll('label.byted-input-inner__wrapper'));"
            "for(var i=0;i<labels.length;i++){"
            "  var inp=labels[i].querySelector('input.byted-input');"
            "  if(inp && inp.getAttribute('readonly')!==null) return inp;"
            "}"
            "return null;})()"
        )
        self.click(sel)

    def _click_preset(self, label):
        """Real-mouse click a date-picker preset radio option (经营 module) by its
        exact text label (自然月/自定义/近30日 etc). Avoids unstable hashed classes."""
        sel = (
            "(function(){"
            "var spans=[].slice.call(document.querySelectorAll('span'));"
            "for(var i=0;i<spans.length;i++){"
            "  var s=spans[i];"
            "  if(s.children.length===0 && s.textContent.trim()===" + json.dumps(label) + "){"
            "    var p=s.parentElement;"
            "    if(p && (p.getAttribute('class')||'').indexOf('byted-radio-group')>=0) return s;"
            "    if((s.getAttribute('class')||'').indexOf('byted-radio')>=0) return s;"
            "    return s;"
            "  }"
            "}"
            "return null;})()"
        )
        return self.click(sel)

    def _detect_picker(self):
        """Return 'advanced' (经营-style radio presets) or 'input' (流量-style input).
        Precise: an input picker needs a readonly date <input>; an advanced picker
        needs a radio group containing both 自然月 and 自定义 presets (so 人群's
        filter radio-groups are not mistaken for the date picker)."""
        return self.eval(
            "return (function(){"
            "function hasDateInput(){"
            "  var labels=[].slice.call(document.querySelectorAll('label.byted-input-inner__wrapper'));"
            "  for(var i=0;i<labels.length;i++){"
            "    var inp=labels[i].querySelector('input.byted-input');"
            "    if(inp && inp.getAttribute('readonly')!==null){"
            "      var v=inp.value||''; var ph=inp.getAttribute('placeholder')||'';"
            "      if(/[～~]|20\\d\\d[-/年.]/.test(v) || /开始时间/.test(ph)) return true;"
            "    }"
            "  } return false;}"
            "function hasDateRadio(){"
            "  var rgs=[].slice.call(document.querySelectorAll('.byted-radio-group'));"
            "  for(var i=0;i<rgs.length;i++){"
            "    var t=(rgs[i].textContent||'').replace(/\\s+/g,'');"
            "    if(t.indexOf('自然月')>=0 && t.indexOf('自定义')>=0) return true;"
            "  } return false;}"
            "if(hasDateInput()) return 'input';"
            "if(hasDateRadio()) return 'advanced';"
            "return 'unknown';})()")

    def _ensure_month(self, month_label, max_steps=12):
        """In an open calendar, navigate (prev) until a panel header matches month_label.
        Returns True if the target month is now visible in any panel."""
        for _ in range(max_steps):
            panels = self.eval(
                "return [].slice.call(document.querySelectorAll('.byted-date-nav')).map(function(n){"
                "return (n.textContent||'').replace(/\\s+/g,'');});")
            if isinstance(panels, list) and any(month_label in p for p in panels):
                return True
            clicked = self.eval(
                "var b=document.querySelector('.byted-date-nav-prev');"
                "if(b){b.click();return 1;} return 0;")
            if not clicked:
                return False
            self.wait(500)
        return False

    def _range_value(self):
        """Return the currently selected range as normalized 'YYYY-MM-DD~YYYY-MM-DD',
        from the 统计周期 input value (input pickers) or the 周期: label (advanced)."""
        v = self.eval(
            "return (function(){"
            "var labels=[].slice.call(document.querySelectorAll('label.byted-input-inner__wrapper'));"
            "for(var i=0;i<labels.length;i++){"
            "  var pre=labels[i].querySelector('.byted-input-prefix');"
            "  if(pre && (pre.textContent.indexOf('统计周期')>=0 || pre.textContent.indexOf('时间')>=0)){"
            "    return labels[i].querySelector('input.byted-input').value || '';"
            "  }"
            "}"
            "return '';})()")
        if v and "~" in v:
            v = v.replace(" ", "").replace("～", "~")
            return v
        pt = self.period_text() or ""
        pt = pt.replace("年", "-").replace("月", "-").replace("/", "-").replace(" ", "")
        return pt

    def set_range(self, y1, m1, d1, y2, m2, d2, max_tries=3):
        """Set custom date range via the 生意经 calendar popup.
        Auto-detects picker type:
          - 'advanced': 经营 module, radio presets (自然月/自定义) -> open calendar.
          - 'input': 流量/商品/人群 etc., readonly <input> -> click to open calendar.
        Then navigate the calendar to the target month and pick start/end (shared logic)."""
        target_start = f"{y1}-{m1:02d}-{d1:02d}"
        target_end = f"{y2}-{m2:02d}-{d2:02d}"
        month_label = f"{y1}年{m1}月"
        for attempt in range(1, max_tries + 1):
            # 0) close any open popup
            self.eval("document.body.click();")
            self.wait(300)
            ptype = self._detect_picker()
            if ptype == "advanced":
                # reset to natural month so target month is reachable in one step
                try:
                    self._click_preset("自然月")
                except Exception:
                    self.click_text("自然月")
                self.wait(2000)
                # open custom calendar (real mouse on 自定义 trigger)
                try:
                    self._click_preset("自定义")
                except Exception:
                    pass
                self.wait(1500)
            elif ptype == "input":
                self._open_input_picker()
                self.wait(1500)
            else:
                return self._range_value()
            # 1) make sure the target month is visible, navigate if needed
            if not self._ensure_month(month_label):
                print("could not surface target month", month_label)
                continue
            # 2) click start date (real mouse)
            s = self._find_month_day(month_label, d1)
            if "x" not in s:
                print("start cell not found:", s)
                continue
            self._click_at(s["x"], s["y"])
            self.wait(600)
            # 3) click end date via JS .click() (more reliable for last-row cells)
            e = self._find_month_day(month_label, d2)
            if "x" not in e:
                print("end cell not found:", e)
                continue
            self._click_day_item(e["panel"], e["idx"])
            self.wait(800)
            # 4) try confirm if a calendar button is present, otherwise auto-applied
            has_btn = self.eval(
                "return !!document.querySelector('.byted-date-panel button.byted-btn-type-primary');")
            if has_btn:
                self.click("document.querySelector('.byted-date-panel button.byted-btn-type-primary')")
                self.wait(500)
            rv = self._range_value()
            if target_start in rv and target_end in rv:
                return rv
        return self._range_value()

    def _click_nav_item(self, item_text, container_hints):
        """Click a nav item, scoping the search to the smallest container that
        contains ALL container_hints (top nav vs sidebar) so duplicate link
        texts (e.g. multiple '流量') don't cause a wrong click."""
        hints_js = "[" + ",".join(json.dumps(h) for h in container_hints) + "]"
        sel = (
            "(function(){"
            "var all=[].slice.call(document.querySelectorAll('*'));"
            "var container=null, bestSize=1e9;"
            "for(var i=0;i<all.length;i++){"
            "  var t=(all[i].textContent||'').replace(/\\s+/g,' ');"
            "  var ok=true; " + hints_js + ".forEach(function(h){ if(t.indexOf(h)<0) ok=false; });"
            "  if(ok){ var sz=all[i].querySelectorAll('*').length; if(sz<bestSize){bestSize=sz; container=all[i];} }"
            "}"
            "if(!container) return null;"
            "var items=[].slice.call(container.querySelectorAll('*'));"
            "for(var j=0;j<items.length;j++){"
            "  if(items[j].children.length===0 && items[j].textContent.trim()===" + json.dumps(item_text) + ") return items[j];"
            "}"
            "return null;})()"
        )
        return self.click(sel)

    def nav_top(self, name):
        """Click a TOP-NAV module (首页/经营/流量/商品/人群/营销/行业竞争/报表集市)."""
        return self._click_nav_item(name, ["首页", "经营", "流量", "商品", "报表集市"])

    def nav_side(self, name):
        """Click a SIDEBAR sub-page (流量概览/门店页流量/内容分析/搜索分析/商品概览/人群资产...)."""
        return self._click_nav_item(name, ["流量概览", "内容分析", "搜索分析", "门店页流量", "人群资产", "商品概览"])

    def switch_module(self, name):
        self.nav_top(name)
        self.wait(1500)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    ld = LD()
    if len(sys.argv) > 1 and sys.argv[1] == "range":
        print("period before:", ld.period_text())
        print("set_range ->", ld.set_range(2026, 7, 1, 2026, 7, 31))
    else:
        print("period:", ld.period_text())
        print("title:", ld.eval("document.title"))
