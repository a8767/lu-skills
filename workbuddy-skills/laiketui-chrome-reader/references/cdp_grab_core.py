"""
cdp_grab_core.py —— 非代运营客户 Chrome(9222) 取数核心模板
复用：改 CLIENT / GROUPID / PERIODS / ROUTES 即可抓新客户/新月份。
依赖：websocket-client（venv 已装）。运行前设 CDP_PORT=9222。

关键稳定模式（实测踩坑结论）：
1. 必须用 PUT /json/new 新建独立 tab，再连其 webSocketDebuggerUrl 导航；
   复用现有 page target 导航会 WebSocket ConnectionAborted。
2. 周期用 URL 参数 startDate/endDate 设，比点日历稳；对比周期自动=上一周期。
3. 数字普遍夹零宽字符，正则前先清洗。
"""

import os, re, sys, json, time, urllib.request, urllib.parse, websocket

PORT = int(os.environ.get("CDP_PORT", "9222"))
HOST = "127.0.0.1"

CLIENT = "龙鲸河漂流"
GROUPID = "1813816605109260"
PERIODS = ["2026-07-01~2026-07-31"]   # 可加多个月份

ROUTES = {
    "overview": "/trade/overview",
    "crowd":    "/customer/my/crowd-assets",
    "flow":     "/flow/my/overview",
    "live":     "/flow/content/my/overview",
    "video":    "/flow/content/my/overview&secondTab=VideoAnalysis",
    "search":   "/search/my/overview",
    "ad":       "/ad/analysis/overview",
    "industry": "/industry/rank",
    "product":  "/product/overview",
}

ZW = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u2060']

def clean(s):
    for z in ZW:
        s = s.replace(z, '')
    return s

# ---------- CDP 底层 ----------
def http_json(path, method="GET", body=None):
    req = urllib.request.Request("http://%s:%d%s" % (HOST, PORT, path),
                                 headers={"Host": "localhost"}, method=method,
                                 data=body)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def new_tab(url="about:blank"):
    # 注意：必须是 PUT，GET 返回 405
    return http_json("/json/new?" + urllib.parse.quote(url, safe=''), method="PUT")

def connect(ws_url):
    return websocket.create_connection(ws_url, sslopt={"cert_reqs": 0}, timeout=90)

_msgid = [0]
def send(ws, method, params=None):
    _msgid[0] += 1
    ws.send(json.dumps({"id": _msgid[0], "method": method,
                        "params": params or {}}))
    # 读到对应 id 的 result（简单线性，适合单命令后取回）
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _msgid[0]:
            return m

def nav(ws, url):
    send(ws, "Page.enable")
    send(ws, "Page.navigate", {"url": url})
    time.sleep(7)

def eval_js(ws, expr):
    r = send(ws, "Runtime.evaluate",
             {"expression": expr, "returnByValue": True,
              "awaitPromise": True})
    return r.get("result", {}).get("result", {}).get("value")

def body_text(ws):
    return eval_js(ws, "document.body.innerText") or ""

def period_ok(txt, per):
    s, e = per.split("~")
    return (s in txt) and (e in txt)

# ---------- 抓取主逻辑 ----------
def grab_one(mod, per):
    s, e = per.split("~")
    url = "https://www.life-data.cn/?groupid=%s%s&startDate=%s&endDate=%s" % (
        GROUPID, ROUTES[mod], s, e)
    tab = new_tab(url)
    ws = connect(tab["webSocketDebuggerUrl"])
    nav(ws, url)
    txt = clean(body_text(ws))
    ws.close()
    # 权限/空白页识别
    if len(txt) < 120 or "暂无该页面权限" in txt:
        print("  [SKIP] %s 权限不足/空白" % mod, flush=True)
        return None
    fn = "dumps/%s_%s_%s.txt" % (CLIENT, mod, per[:7].replace("-", ""))
    open(fn, "w", encoding="utf-8").write(txt)
    print("  [OK] %s %d chars -> %s" % (mod, len(txt), fn), flush=True)
    return txt

if __name__ == "__main__":
    for per in PERIODS:
        print("周期", per, flush=True)
        for mod in ROUTES:
            grab_one(mod, per)
