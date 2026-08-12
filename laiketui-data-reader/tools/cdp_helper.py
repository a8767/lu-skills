#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cdp_helper.py - 自研 Python CDP 客户端（抖音来客/生意经数据读取连接层）
基于 websocket-client，强制 IPv4 以绕过 localhost→IPv6(::1) 连接失败。
支持: targets / nav / eval / text / click / rclick / fill / wait / screenshot

连接策略：通过浏览器级端点 devtools/browser 列出/创建 page 目标，
再以 devtools/page/<targetId> 连接（/json 返回的 page 目标 debugger 端点常为死链）。

用法:
  python cdp_helper.py targets
  python cdp_helper.py nav "https://www.life-data.cn/?groupid=1736233383495694" [--urlhint life-data]
  python cdp_helper.py eval "document.cookie" [--urlhint life-data]
  python cdp_helper.py text "body" [--urlhint life-data]
  python cdp_helper.py click "document.querySelector('x')" [--urlhint life-data]
  python cdp_helper.py rclick "document.querySelector('x')" [--urlhint life-data]
  python cdp_helper.py fill "document.querySelector('x')" "文本" [--urlhint life-data]
  python cdp_helper.py wait 2000 [--urlhint life-data]
  python cdp_helper.py screenshot out.png [--urlhint life-data]
"""
import sys
import json
import time
import base64
import urllib.request
import argparse
import websocket

DEBUG_PORT = 9223
BROWSER_WS = None  # 延迟解析


def _http_get_json(path):
    url = f"http://127.0.0.1:{DEBUG_PORT}{path}"
    req = urllib.request.Request(url, headers={"Host": "127.0.0.1"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def browser_ws_url():
    global BROWSER_WS
    if BROWSER_WS:
        return BROWSER_WS
    v = _http_get_json("/json/version")
    u = v["webSocketDebuggerUrl"]
    # 部分 Edge 构建在 webSocketDebuggerUrl 中省略端口（如 ws://127.0.0.1/devtools/...），
    # 必须强制补齐为 127.0.0.1:DEBUG_PORT，否则会连到 80 端口被拒（ConnectionRefused 10061）。
    import re
    u = re.sub(r"^ws://[^/]+", "ws://127.0.0.1:%d" % DEBUG_PORT, u)
    BROWSER_WS = u
    return u


def _browser_cmd(ws, method, params=None, timeout=30):
    ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        m = json.loads(ws.recv())
        if m.get("id") == 1:
            if "error" in m:
                raise RuntimeError(f"browser cmd error {m['error']}")
            return m.get("result")
    raise TimeoutError("browser cmd timeout")


def find_or_create_target(urlhint=None, create_url=None):
    bws = browser_ws_url().replace("localhost", "127.0.0.1")
    ws = websocket.create_connection(bws, timeout=30)
    try:
        res = _browser_cmd(ws, "Target.getTargets")
        targets = res.get("targetInfos", [])
        # 过滤掉非真实页面（about:blank / edge:// / http://data/ 等占位）
        pages = [t for t in targets
                 if t.get("type") == "page"
                 and t.get("url")
                 and not t["url"].startswith(("about:blank", "edge://", "http://data/", "chrome://"))]
        if urlhint:
            for t in pages:
                if urlhint in t.get("url", "") or urlhint in (t.get("title") or ""):
                    return t["targetId"]
        if pages:
            # 无 hint 时挑第一个真实页面
            return pages[0]["targetId"]
        # 没有可用页面 → 新建
        res = _browser_cmd(ws, "Target.createTarget",
                           {"url": create_url or "about:blank"})
        return res["targetId"]
    finally:
        ws.close()


def page_ws_url(target_id):
    return f"ws://127.0.0.1:{DEBUG_PORT}/devtools/page/{target_id}"


class CDP:
    def __init__(self, target_id):
        self.ws = websocket.create_connection(page_ws_url(target_id), timeout=30,
                                             enable_multithread=False)
        self._id = 0

    def send(self, method, params=None, timeout=30):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(msg))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = self.ws.recv()
            obj = json.loads(raw)
            if obj.get("id") == self._id:
                if "error" in obj:
                    raise RuntimeError(f"CDP error {obj['error']}")
                return obj.get("result")
        raise TimeoutError("CDP response timeout")

    def enable(self):
        for m in ("Page.enable", "Runtime.enable"):
            try:
                self.send(m, timeout=5)
            except Exception:
                pass

    def navigate(self, url):
        return self.send("Page.navigate", {"url": url}, timeout=20)

    def evaluate(self, expr, timeout=20):
        code = f"(function(){{ {expr} }})()"
        res = self.send("Runtime.evaluate",
                        {"expression": code, "returnByValue": True,
                         "awaitPromise": True}, timeout=timeout)
        if res.get("exceptionDetails"):
            exc = res["exceptionDetails"]
            raise RuntimeError(f"JS exc: {exc.get('text')} {exc.get('exception',{}).get('description')}")
        r = res.get("result", {})
        if "value" in r:
            return r["value"]
        if r.get("type") == "undefined":
            return None
        return r.get("description")

    def get_text(self, selector="body"):
        expr = (f"var el=document.querySelector({json.dumps(selector)});"
                f"return el? el.innerText : null;")
        return self.evaluate(expr)

    def _rect_center(self, expr):
        return self.evaluate(
            f"var el={expr}; if(!el) return null; "
            f"var r=el.getBoundingClientRect();"
            f"return {{x:r.x+r.width/2, y:r.y+r.height/2, w:r.width, h:r.height}};")

    def click(self, expr, real=True):
        rect = self._rect_center(expr)
        if not rect:
            raise SystemExit("element not found for click")
        if real:
            self._mouse(rect["x"], rect["y"])
            return "real-clicked"
        return self.evaluate(f"var el={expr}; if(el){{el.click(); return 'clicked';}} return 'none';")

    def _mouse(self, x, y):
        for typ in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {
                "type": typ, "x": x, "y": y, "button": "left",
                "clickCount": 1 if typ == "mousePressed" else 0, "modifiers": 0,
            }, timeout=10)

    def fill(self, expr, text):
        self.evaluate(
            f"var el={expr}; if(el){{ el.focus(); "
            f"if(el.select){{try{{el.select();}}catch(e){{}}}} "
            f"if(el.setSelectionRange){{try{{el.setSelectionRange(0, el.value.length);}}catch(e){{}}}} }}")
        time.sleep(0.2)
        self.send("Input.insertText", {"text": text}, timeout=10)
        return "filled"

    def wait(self, ms):
        time.sleep(ms / 1000.0)
        return "waited"

    def screenshot(self, path):
        res = self.send("Page.captureScreenshot", {"format": "png"}, timeout=30)
        data = base64.b64decode(res["data"])
        with open(path, "wb") as f:
            f.write(data)
        return f"saved {path} ({len(data)} bytes)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command")
    ap.add_argument("arg", nargs="*")
    ap.add_argument("--urlhint")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    if args.command == "targets":
        for t in _http_get_json("/json"):
            if t.get("type") == "page":
                print(f"{t.get('id')}\t{t.get('url')}\t{t.get('title')}")
        return

    if args.command == "nav":
        # 确保存在目标页，再导航
        tid = find_or_create_target(args.urlhint, create_url=args.arg[0])
        cdp = CDP(tid)
        cdp.enable()
        print(cdp.navigate(args.arg[0]))
        return

    # 其余命令：定位目标页（必要时新建空白页）
    tid = find_or_create_target(args.urlhint)
    cdp = CDP(tid)
    cdp.enable()

    cmd, a = args.command, args.arg
    if cmd == "eval":
        print(json.dumps(cdp.evaluate(a[0], timeout=args.timeout), ensure_ascii=False))
    elif cmd == "text":
        print(cdp.get_text(a[0]) if a else cdp.get_text())
    elif cmd in ("click", "rclick"):
        print(cdp.click(a[0], real=(cmd == "rclick")))
    elif cmd == "fill":
        print(cdp.fill(a[0], a[1]))
    elif cmd == "wait":
        print(cdp.wait(int(a[0])))
    elif cmd == "screenshot":
        print(cdp.screenshot(a[0]))
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
