---
name: laiketui-chrome-reader
description: 抖音来客/生意经 非代运营客户的月度/趋势经营复盘取数 + 报告生成全链路。适用于来客后台只登录在用户个人 Chrome（林客/Edge 无权限）的客户：用独立 Chrome 调试实例（端口9222 + 新建独立tab导航）稳定复用登录态，URL 参数设周期，跨月抓取经营/流量/直播/视频/搜索/投放/人群/行业等模块，解析后生成九章式月报或 4-N月趋势报告，并备份至飞书。当用户说"龙鲸河/某非代运营客户的X月复盘/趋势复盘"、且 Edge+林客跳不了客户后台时使用。
version: 1.0.0
agent_created: true
display_name: "非代运营客户Chrome取数"
display_name_en: "Laiketui Chrome Non-Agency Reader"
description_zh: "非代运营客户（个人Chrome登录）的生意经取数 + 月报/趋势报告生成全链路"
description_en: "Read 生意经 for non-agency clients (personal Chrome login) and generate monthly/trend review reports."
visibility: "private"
---

# 非代运营客户 Chrome 取数 + 复盘报告生成（v1.0.0）

## 用途
针对 **林客/Edge 无权限、来客后台只登录在用户个人 Chrome** 的客户（如龙鲸河漂流），
复用用户真实登录态，稳定抓取抖音生意经（life-data.cn）多模块数据，解析后产出
**月度复盘（九章式）** 或 **多月份趋势复盘** 报告，并自动备份飞书。

> 本 skill 由 2026-08-11~08-15 龙鲸河漂流 4-7月复盘实测跑通后提炼，所有坑均为真实踩过。

## 何时使用
- 用户要某**非代运营客户**（个人 Chrome 登录来客）的月度/趋势经营复盘。
- 用户确认："Edge/林客跳不了这个客户，来客在我 Chrome 里登录好了"。
- 目标客户在 `laiketui-data-reader` 的林客切换路径下搜不到（如龙鲸河 groupid 1813816605109260）。
- ⚠️ 若客户在代运营公司下（林客可搜到），**优先用 `laiketui-data-reader` 的 Edge+林客路径**，本 skill 仅用于非代运营场景。

## 前置依赖
- **浏览器 = 用户个人 Chrome**（`C:\Users\Admin\AppData\Local\Google\Chrome\Application\chrome.exe`）。
- **连接层 = 自研 Python CDP 客户端 `tools/cdp_helper.py`**（同 `laiketui-data-reader` 项目内），
  已支持 `CDP_PORT` 环境变量切换端口（默认 9223）。本场景所有脚本前加 `CDP_PORT=9222`。
- venv：`C:\Users\Admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（已装 `websocket-client`）。
- 用户**必须已在其 Chrome 登录来客/生意经**（扫码）。本 skill **不自动登录**。
- 交付依赖 `lark-cli`（飞书已连接）做文档备份。

## 核心原则（含实测踩坑）
1. **来客登录是会话级 cookie，Chrome 重启即失效** —— 让用户在调试窗口里登录后，全程不重启。
2. **复用登录态，绝不自动登录/验证码**。
3. **独立 user-data-dir 新实例**：避免复用残留 Chrome 进程吞掉 `--remote-debugging-port` 参数
   （用户自己"重启带参"常失败，端口起不来）。
4. **用"新建独立 tab"导航，不要复用现有 page target** —— Chrome 复用旧 target 导航会
   `WebSocket ConnectionAborted`，每步都新建 tab 才稳定（Edge 无此问题）。

## 流程

### 0. 启动独立调试版 Chrome（不碰用户当前窗口）
用 PowerShell 脱离 shell 启动，带独立 user-data-dir，打开来客登录页：
```powershell
$chrome = "C:\Users\Admin\AppData\Local\Google\Chrome\Application\chrome.exe"
Start-Process -FilePath $chrome -ArgumentList `
  '--remote-debugging-port=9222','--remote-allow-origins=*',`
  '--user-data-dir=C:\Users\Admin\.workbuddy\chrome-debug-profile',`
  'https://life.douyin.com/'
```
等约 6 秒，验证端口：
```bash
python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',9222));print('OPEN')"
```
让用户在新窗口**扫码登录来客 → 切到目标客户**（如龙鲸河漂流）。用户说"好了"后再继续。

> **诊断端口**：用 `netstat -ano | findstr LISTENING | findstr 922`；注意 **9227 是本机阿里云盘 aDrive，非浏览器**。

### 1. 连接 + 确认登录与当前商家
```python
# tools/probe_sjy_chrome.py 思路：
req = urllib.request.Request('http://127.0.0.1:9222/json', headers={'Host':'localhost'})
ts = json.loads(urllib.request.urlopen(req, timeout=8).read())
for t in ts:
    if t.get('type')=='page':
        print(t.get('title'), t.get('url'))   # 找到 life-data.cn 目标页
```
打开生意经后从 URL 拿到 `groupid`（龙鲸河=1813816605109260），确认右上角商家名正确。

### 2. 设周期（URL 参数法，比点日历稳）
在生意经各模块 URL 后追加 `&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD` 即可**整月/跨月生效**，
对比周期自动=上一周期。对以下模块均生效：
- 经营概览 `/trade/overview`
- 人群资产 `/customer/my/crowd-assets`
- 流量概览 `/flow/my/overview`
- 内容分析（直播）`/flow/content/my/overview`
- 门店页 `/store/my/single/overview`
- 搜索 `/search/my/overview`
- 投放 `/ad/analysis/overview`
- 行业竞争 `/industry/rank`
- 商品（龙鲸河有）`/product/...`

> 视频/获客卡子标签页（`secondTab=VideoAnalysis/CardAnalysis`）可能**返回"暂无该页面权限"空白页** → 跳过，
> 短视频/获客卡成交金额改从**经营概览「成交来源及体裁」表**取（部分客户如驭龙峡/新海府不披露该表 → 标"—"）。
> 行业竞争页有时只渲染菜单（93字），需点「门店榜/商家榜」tab 后再 dump。

### 3. 新建独立 tab 抓取（关键稳定模式）
**务必用 PUT 新建 tab，不要复用现有 page target**（GET 会 405，复用会 ConnectionAborted）：
```python
def new_tab(port=9222, url="about:blank"):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/json/new?%s" % (port, urllib.parse.quote(url, safe='')),
        headers={'Host':'localhost'}, method='PUT')
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

def connect_tab(ws_url):
    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs":0},
                                     sockopt=..., timeout=60)
    return ws
```
每抓一个模块：**new_tab → 连 ws → 导航到带日期参数的模块 URL → sleep 7 → 关浮层 → 校验周期文本
`20\d\d-\d\d-\d\d~20\d\d-\d\d-\d\d` 已生效 → dump `document.body.innerText`** → 落盘 `dumps/<客户>_<mod>_<mon>.txt`。

### 4. 解析（结构化为 JSON）
通用模式（见 `tools/parse_month.py` / `tools/parse_longjing_trend.py`）：
- 读 `dumps/<客户>_<mod>_<mon>.txt`，用正则提字段。
- **零宽字符清洗**（必须先做）：`for z in ['\u200b','\u200c','\u200d','\ufeff','\u2060']: t=t.replace(z,'')`
  否则行业竞争「排名第​2​名」、金额夹零宽会匹配失败。
- **经营城市换行容错**：`经营城市[:：]?\s*(\S+)`（新海府是"海口市/文昌市"换行，非同行冒号）。
- **直播「直播间成交金额」实时值污染**：页面顶部"大屏"区有正在直播的实时小值（如¥5,132），
  **真实月值取「核心数据」区或 AI 洞察文本"直播间成交金额X.XX万"**（龙鲸河真实=¥184,281.60）。
  解析器只从「核心数据」标签之后提取。
- **直播场次表过滤挂播**：达人直播间时长字段可能显示"216小时"（跨天累计），
  `live_rooms` 过滤 `hours_of(时长) > 48` 并**按成交金额降序取 TOP5**。
- **退款金额可能 > 成交金额**（龙鲸河7月退款¥81.7万 vs 成交¥29.6万，洪水退票）→ 如实呈现，
  报告里标注"退款为当期发生口径，可能含前期退票"。
- **商品标签差异**：旧标签"在售/动销"在新版为"全部商品数/常规动销商品数"，用并集匹配。
- 落盘 `data/<客户>/records/<YYYY-MM-DD>_month.json`（月度）或趋势聚合 JSON。

### 5. 生成报告
- **月度复盘（九章式）**：`tools/gen_month_reports.py`（读 `_month_parsed.json`）→
  `reviews/<客户>__month_<YYYY-MM>.md`。
  - 模板：〇核心结论一页纸 / 一门店核心数据 / 二流量场景+体裁 / 三直播短视频 / 四本地推投放ROI /
    五人群 / 六搜索 / 七行业竞争 / 八评价口碑 / 九AI解读P0-P2 / 十数据说明。
  - **AI 解读字典需 per-client 条目**：在 `gen_month_reports.py` 的 `AI = {...}` 里加该客户
    （龙鲸河已加）；未加则行业竞争章节降级显示榜单排名，AI 解读为空。
  - 行业排名：从 `/industry/rank` 取「品类范围 + 经营城市 + 门店榜/商家榜第X名」。
- **趋势复盘（多月份对比）**：`tools/gen_longjing_trend.py`（读 `dumps/<客户>_trend.json`）→
  `reviews/<客户>__trend_<起>-<止>.md`，按"4月预售蓄水→5月消化→6月平稳→7月旺季"四阶段叙事。
- 重跑即刷新，勿手写。

### 6. 飞书备份（用户习惯：生成文档同步飞书）
```bash
cd reviews
lark-cli docs +create --doc-format markdown --content @<客户>__month_2026-07.md \
  --title "龙鲸河漂流 2026年7月经营复盘" --as user
```
返回的 doc 链接即备份。合并/趋势版同样处理。

## 工具链（workspace 内已落地，可直接复用/参考）
- `tools/cdp_helper.py`：CDP 客户端，支持 `CDP_PORT` 切端口。
- `tools/grab_longjing_july.py`：龙鲸河 7 月抓取（新tab + URL参数，11模块）。
- `tools/grab_longjing_trend.py` + `tools/retry_flow_45.py`：4-6月趋势抓取 + 4/5月流量重抓。
- `tools/parse_month.py` / `tools/gen_month_reviews.py`：月报解析/生成（含 live 核心数据区取值、商品标签并集）。
- `tools/parse_longjing_trend.py` / `tools/gen_longjing_trend.py`：趋势解析/生成。
- `tools/upload_*_feishu.py`：lark-cli 备份脚本模板。

> 换客户时：改 `groupid`、客户显示名、抓取月份、AI 字典条目即可，流程不变。

## 常见坑速查
| 现象 | 原因 | 处理 |
|------|------|------|
| 端口 9222 连不上 | 用户"重启带参"被残留进程吞参 | 用独立 `--user-data-dir` 新实例启动 |
| WebSocket ConnectionAborted | 复用旧 page target 导航 | 每步 `PUT /json/new` 新建 tab |
| 行业排名/"排名第X名"提取空 | 数字夹零宽 `\u200b` | 正则前先清洗零宽字符 |
| 直播成交金额异常小 | 取了顶部"正在直播"实时值 | 从「核心数据」区/AI 文案取值 |
| 退款 > 成交 | 当期退款含前期退票（洪水等） | 如实呈现 + 数据说明标注 |
| 视频/获客卡子模块空白 | 账号无权限 | 跳过，改从经营概览体裁表取；无表则"—" |
| PUT /json/new 返回 405 | 用了 GET | 必须 method='PUT' |
| stdout 重定向文件无输出 | Python 缓冲 | 用 `python -u` 运行 |

## 数据质量红线
- 抓经营概览前**先确认周期=目标月且核心数据已渲染**，否则用「流量概览·场景成交总计」交叉验证。
- 经营成交金额 ≡ 流量场景总计（已验证口径一致），可互校。
- 所有"—"均因平台/权限，非漏抓；报告需列明缺口。
