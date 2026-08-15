---
name: laiketui-data-reader
description: 读取抖音来客（life.douyin.com 商家后台）及其「生意经」数据中心（life-data.cn）的经营数据，支持门店管理员账号在多客户间切换读取。覆盖经营概览、流量（直播/视频/搜索）、内容分析、人群资产、团购、订单、达人分账、评价。通过浏览器自动化复用用户真实登录态，登录后抓取指标并导出为 CSV/Excel/复盘报告。支持周/月/季/年四维度复盘（统计/对比/趋势/目标完成度）。当用户要查来客后台数据、导出团购/核销明细、看经营看板、做本地生活经营复盘/周报/月报/季报/年报取数时使用。
version: 1.4.1
agent_created: true
display_name: "来客后台数据读取"
display_name_en: "Laiketui Data Reader"
description_zh: "读取抖音来客/生意经数据中心经营数据（支持多客户切换 + 周/月/季/年四维度复盘），浏览器自动化复用登录态并导出。"
description_en: "Read Douyin Laiketui merchant backend & 生意经 (life-data.cn) data, supports multi-merchant switching and weekly/monthly/quarterly/yearly review, export to CSV/Excel."
visibility: "private"
---

# 抖音来客后台数据读取（Laiketui Data Reader）v1.4.1

## 用途
通过浏览器自动化读取「抖音来客」商家后台及其「生意经」数据中心的经营数据，把抓取到的指标整理成 CSV/Excel/**多维度复盘报告**。

**重要**：本 skill 经真实实测跑通（2026-07-14，青石峡漂流门店管理员账号），后续又经太湖梦华等客户验证并迭代为 **Edge 浏览器 + 自研 Python CDP 客户端**方案。以下流程为已验证路径。

## 何时使用
- 用户要查/导出抖音来客后台任何经营数据（GMV、核销、订单、退款、达人分账等）。
- 用户说"看经营看板""导出团购明细""统计核销率""拉达人带货数据"。
- 用户要做经营复盘/分析报告，且明确了**周期**：**周复盘 / 月复盘 / 季复盘 / 年复盘**。
- 用户是**门店管理员账号、下挂多家客户**（如代运营公司）：需在多家客户之间切换读取、分别导出（文件名带客户名）。
- 用户在做本地生活项目（团购、文旅、餐饮、加油站等）的对账或数据复盘。
- **2026-08-15 新增**：用户是**服务商 / 代运营公司**，要一次拉出**旗下全部代运营商家**在某时间窗的核销GMV / 退款GMV / 总预估佣金 / 服务商预估佣金，并测算推广佣金成本（=总-服务商）。入口在**抖音林客 (`life-partner.cn`) → 商家数据 → 探索列表**，跑 `tools/extract_daiyunying.py` 即可。

## 前置依赖（本机已验证可用）

> **2026-07-22 更新**：用户明确偏好 **Edge 浏览器**；agent-browser 在本环境出现子进程脱离、CDP 握手超时等问题，**已改用自研 Python CDP 客户端**作为可靠连接层。

- **浏览器 = Microsoft Edge**（用户偏好，稳定复用登录态）。
  - 路径：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
  - 启动参数必须包含 **`--remote-debugging-port=9223 --remote-allow-origins=*`**，否则外部 CDP 客户端会被 403 拒绝。
  - 一键启动脚本见 `tools/edge_debug_launch.bat`（已含 `--remote-allow-origins=*`）。
- **连接层 = 自研 Python CDP 客户端 `tools/cdp_helper.py`**。
  - 基于 `websocket-client`，通过预连 IPv4 套接字绕过 `getaddrinfo` IPv6 问题。
  - 支持 `eval/nav/text/click/fill/wait/targets/ui/rclick`（`rclick` 用 CDP Input 真实鼠标事件，可触发 `window.open`/React onClick）。
- **历史备用：agent-browser / Chrome**。
  - 若 Edge 登录态失效，可退回 Chrome（`--remote-debugging-port=9222 --remote-allow-origins=*`）。
  - agent-browser 在本环境不稳定，仅作备选。
- 用户**必须已在其浏览器登录过来客后台**（手机号验证码）。本技能**不自动输入账号密码/验证码**，只复用已有登录态。
- **聚合引擎 = `scripts/aggregate.py`**（纯标准库 Python），用于四维度复盘的统计/对比/趋势/目标完成度计算与报告生成。

## 核心原则（含实测踩坑）
1. **来客登录是「会话级 cookie」——Chrome 一重启就失效**：实测确认，来客/生意经的登录会话 cookie（`sessionid_*`、`uid_tt_*`、`sid_tt_*`）在关闭 Chrome 后即被清除，**磁盘上存的 cookie 无法在重启后的浏览器里恢复登录**。
   - **正确做法**：用带调试端口的 Chrome **让用户当场登录一次**，登录后保持该 Chrome 开启、期间不要重启，本会话内直接取数。
2. **复用登录态，绝不自动登录**：只能复用用户真实 Chrome 的会话，不能自动填验证码或账号密码。
3. **先 snapshot 后操作**：每次交互前 `$AB snapshot` 拿 `@eN` 元素引用，操作后立刻 `snapshot`/`screenshot` 验证。
4. **只读取，不修改**：默认不做上架/改价/退款等写操作；用户明确要求时二次确认后再执行。
5. **入口先确认**：导航文案可能随版本调整，首次进入若路径不符，先用 `snapshot`/`screenshot`/`get url` 确认当前页面。

## 流程

### 0. 启动可连接的 Edge（让用户当场登录——最关键一步）
来客数据登录后才能看。来客会话 cookie 重启即丢，所以流程是：**开一个带调试端口的 Edge → 让用户在这个窗口里登录 → 连接取数 → 期间不重启**。

**方式 A：双击一键启动脚本**（推荐）
```bash
C:\Users\Admin\Desktop\edge_debug_launch.bat
# 或项目内副本
E:\AI助理\2026-07-14-12-56-08\tools\edge_debug_launch.bat
```
脚本内容（CRLF+GBK，确保中文路径不炸）：
```batch
start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" ^
  --remote-debugging-port=9223 ^
  --remote-allow-origins=* ^
  --user-data-dir="C:\Users\Admin\AppData\Local\Microsoft\Edge\User Data"
```

**方式 B：用 PowerShell `Start-Process` 脱离 shell 启动**
```powershell
Start-Process -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  -ArgumentList '--remote-debugging-port=9223','--remote-allow-origins=*',`
  '--user-data-dir=C:\Users\Admin\AppData\Local\Microsoft\Edge\User Data','--no-first-run'
```

> **关键参数**：`--remote-allow-origins=*` 必须加，否则外部 CDP WebSocket 客户端握手时会被 **403 Forbidden** 拒绝（此前 agent-browser 全部卡死、Python 报 10061 的根因即为此）。

启动后等约 7 秒，验证端口监听：
```bash
curl -s http://127.0.0.1:9223/json/version   # 应返回 Edg 信息
```

然后连接，并**让用户在此 Edge 窗口内完成来客登录**（手机号+短信验证码，勾选协议框）。登录后用 Python CDP 客户端复核：
```bash
python tools/cdp_helper.py targets
python tools/cdp_helper.py eval "document.cookie" --urlhint life-data
# 出现 sessionid_*/uid_tt_*/sid_tt_* 即已登录
```

### 1. 进入「生意经」数据中心（推荐路径：林客后台跳转）
用户偏好路径：**抖音林客（life-partner.cn）→ 商家运营 → 商家概览 → 搜索客户 → 商家后台** → 自动跳转来客并带入 groupid → 顶部导航「生意经」。

```text
抖音林客 (life-partner.cn)
  → 左侧菜单「商家运营」→「商家概览」
    → 右上角搜索框输入「太湖梦华」
      → 找到目标行后点击「商家后台」按钮
        → 自动跳转到来客 (life.douyin.com) 并带入 groupid
          → 点击顶部导航「生意经」进入数据中心
```

**多客户管理员切换（核心场景）**：
- 林客商家概览右上角搜索框支持按商家ID/名称/品牌名**模糊查找**。
- 每行「操作」列有「商家后台」按钮，点击后自动在新标签页打开该商家来客后台。
- 生意经内如需切换商户，可直接点页面右上角当前商户名 → 「切换商户」→ 搜索/选择目标商户（最快）。
- **每家客户单独读取、单独导出**，文件名带客户名。

**生意经 URL 直接带 groupid 切户**（已在生意经内时最快）：
```
https://www.life-data.cn/?groupid=1852933719817356
```

### 1.5 切换商户（2026-07-15 实测跑通）

> **实测确认**：来客后台右上角商户名旁可呼出「切换商户」入口，已登录态下随时切换下挂商家，无需重登。已验证：郑州爪娃岛 → 驭龙峡漂流（URL `groupid` 从 `1776747848611853` → `1867591074882572`）。

**入口是两层嵌套（实测关键）**：
1. 右上角有「蓝抓联盟」头像 + 当前公司名（如 `郑州爪娃岛商贸有限公司`，是一个 `generic clickable` 元素）。
2. **点击公司名** → 弹出下拉菜单 → 菜单里有 `切换商户` 按钮。
3. 点 `切换商户` → 弹出「切换公司」对话框（含搜索框 + 商户列表）。

**⚠️ 自动化踩坑（重要）**：
- 下拉菜单是 toggle 且 `@eN` 引用在每次 snapshot 后重新编号，**直接 `$AB click @eN` 点"切换商户"极易因焦点丢失/ref 失效而失败**（实测报 `Could not locate element`）。
- **实测可靠方案：用 `eval` 按文本定位并直接 `click()`**，`snapshot`/`click` 之间不要多此一举地重新 snapshot。

**完整可用脚本（已验证通过）**：
```bash
AB="…agent-browser.js"; export CHROME_PATH="…/chrome.exe"

# ① 点击右上角当前公司名，呼出下拉（公司名元素是含公司名文本的 generic clickable）
$AB snapshot | grep -n "郑州爪娃岛商贸有限公司"   # 定位公司名行，记其 clickable 父 ref（如 e263）
$AB click e263                                   # 呼出下拉菜单
sleep 1

# ② 用 eval 按文本点击"切换商户"按钮（绕过 ref 失效）
$AB eval "(function(){var all=document.querySelectorAll('*');for(var i=0;i<all.length;i++){var e=all[i];if(e.children.length===0&&e.textContent.trim()==='切换商户'){var el=e;for(var j=0;j<5&&el;j++){var tag=el.tagName;var role=el.getAttribute('role');var cls=el.getAttribute('class')||'';if(tag==='BUTTON'||role==='button'||cls.indexOf('clickable')>=0||cls.indexOf('pointer')>=0){el.click();return 'clicked:'+tag;}el=el.parentElement;}return 'no-parent';}}return 'notfound';})()"
sleep 1   # 弹出「切换公司」对话框

# ③ 在搜索框（textbox，位于 LabelText 内）输入目标商家名，模糊过滤
$AB snapshot | grep -n "textbox"                 # 找到搜索框 ref（如 e130）
$AB fill e130 "驭龙峡"
sleep 1.5

# ④ 选中过滤出的列表项（clickable generic，文本=商家名）
$AB snapshot | grep -n "驭龙峡漂流"               # 找到列表项 ref（如 e131）
$AB click e131                                   # 选中后底部出现「取消/确认」按钮
sleep 1

# ⑤ 点击「确认」完成切换
$AB snapshot | grep -n '"确认"'                   # 找到确认按钮 ref（如 e12）
$AB click e12
sleep 3
```

**验证切换成功**：
- `$AB get url` → `groupid` 改变（实测 `1776747848611853` → `1867591074882572`）。
- `$AB snapshot` → 右上角公司名变为目标商家（如 `驭龙峡漂流`），原商家名消失。

**注意事项**：
- 搜索框支持**模糊匹配**，输入部分名称（如「驭龙峡」）即可过滤列表。
- 列表项需**先点击选中（高亮）**后，底部「确认」按钮才出现/可点；未选中时点确认无效。
- 切换后页面**完整刷新**，需等加载完成再操作。
- 与步骤 1「首次进入生意经的商户选择弹窗」是**两个不同入口**：前者仅首访弹出；本入口任意时刻可用。
- 公司名 ref（e263 等）**每次会话不同**，务必每次先 `snapshot` 定位，不要硬编码 ref。

### 2. 设置时间范围（按复盘周期）
- 数据中心默认常显示"今天"或"近7天"，需改为目标周期。
- **日期选择决策树（用户截图教学，2026-08-06）**：详见 `references/user-taught-methods.md` 方法八。
  - **月复盘** → 优先点「自然月」→ 选目标月份（自动 1 日~月末）。
  - **周复盘** → 仅当**今天是周一**时，直接点「近7天」= 上周完整自然周；**周二~周日禁止用「近7天」**，必须走「自定义」选上周一~上周日。
  - **特殊/跨月周期** → 点「自定义」→ 双月日历面板选起始日、结束日（跨月先起点后终点）。
- 新版 `byted-date` 日历无独立确认按钮，第二次点结束日格后自动关闭生效；若真实鼠标/JS click 不响应，用 **React fiber `props.onClick`** 点击日格（2026-08-01 已验证）。
- 各一级模块（经营/流量/内容/投放/人群）周期相互独立，切模块后需重设。
- **四维度复盘对应的时间窗**（由 `aggregate.py period` 统一计算，避免算错边界）：

  | 复盘类型 | 时间窗示例 | 说明 |
  |----------|------------|------|
  | 周复盘 | 上周一~上周日（如 07/06~07/12） | 自然周 |
  | 月复盘 | 上月 1 日~月末（如 06/01~06/30） | 自然月 |
  | 季复盘 | 上季首月 1 日~末月末（如 Q2: 04/01~06/30） | 自然季 |
  | 年复盘 | 上年 1/1~12/31（如 2025-01-01~2025-12-31） | 自然年 |

- 用 `snapshot`/`screenshot` 确认时间范围已生效（页面会显示 `2026-07-06 ~ 2026-07-12`）。

### 3. 逐模块读取（标签：首页 | 经营 | 流量 | 商品 | 人群 | 排版 | 行业竞争）
各模块字段与选择器见 `references/modules.md`。实测重点模块：
- **经营概览**：成交金额、核销金额、退款金额、预约金额（金额为主；券数需进详情或「交易查询」）。
- **流量**：总曝光次数、门店页访问人数；**来源表**含直播/视频/搜索各自的曝光人数、成交金额、核销金额、转化率。
- **内容分析**（流量下的子标签，或独立标签）：
  - 直播：直播间成交金额、直播核销金额、直播退款金额、**直播时长**（秒，需 ÷3600 换算小时）、**直播场次数**、直播间曝光人数、观看人数、转化率。
  - 视频：短视频成交金额、视频播放量、种草价值、视频成交券数。
- **人群资产**：新客成交数、老客成交数、复购人数/复购率、人群画像（年龄/性别/城市/消费力分布）。
- **评论/评价**：新增好评、新增中差评数。
- **对比/趋势/目标**（四维度复盘额外需要）：
  - **对比数据**：开启页面「对比」开关（环比 vs 上一周期 / 同比 vs 去年同期），读取各指标 delta；也可由 `aggregate.py` 从已存历史记录自动计算（见步骤 4.5）。
  - **趋势数据**：把日期范围拉到更长窗口（如月复盘拉 12 个月），读取逐子周期序列；或由 `aggregate.py review` 从已存多个周期记录拼出。
  - **目标完成度**：目标值来自 `config/targets.json`（运营维护），由脚本算完成率。

提取方式（Python CDP 客户端）：
```bash
# 看板指标：定位元素后读文本
python tools/cdp_helper.py text "body" --urlhint life-data
python tools/cdp_helper.py eval "document.querySelector('选择器').innerText" --urlhint life-data

# 真实点击（React 组件需要可信事件）
python tools/cdp_helper.py rclick "document.querySelector('选择器')"

# 表格：直接取二维数组（喂给 normalize.py）
python tools/cdp_helper.py eval "JSON.stringify(Array.from(document.querySelectorAll('table tbody tr')).map(r=>Array.from(r.children).map(c=>c.innerText.trim())))" --urlhint life-data > out/raw.json

# 或截图后由视觉读取（需扩展 cdp_helper.py 支持 Page.captureScreenshot）
```

历史 agent-browser 命令仍可用（若环境恢复稳定）：
```bash
# 看板指标：snapshot 找 @eN，逐个读
$AB get text @eN
# 表格：直接取二维数组（喂给 normalize.py）
$AB eval "Array.from(document.querySelectorAll('table tbody tr')).map(r=>Array.from(r.children).map(c=>c.innerText.trim()))" > out/raw.json
# 或截图后由视觉读取
$AB screenshot out/board.png
```
分页：先读总条数/页数，循环点下一页追加，至末页。详见 `references/extraction.md`。

### 4. 导出与规整（原始表数据）
```bash
python scripts/normalize.py out/raw.json --module 团购数据 --out "out/客户_团购数据_$(date +%F).csv"
python scripts/normalize.py out/raw.json --module 核销分析 --xlsx --out "out/客户_核销分析.xlsx"
```
`normalize.py`：识别表头、统一字段名（中英文映射见 `modules.md`）、把"万元/%/¥"还原为数值、Excel 模式按门店拆分多 sheet。

### 4.5 四维度复盘报告（核心新增能力）
把**本周期抓取的全部指标**存为一条 canonical 记录，再用 `aggregate.py` 生成含**四类数据**的复盘报告：

```bash
# (a) 存记录：把本次抓到的 stats 写成 JSON
python scripts/aggregate.py collect \
  --client 青石峡漂流 --type week --ref 2026-07-14 --completed \
  --stats out/qingshixia_week_stats.json --data-dir data

# (b) 若要做月/季/年复盘，且只有更细周期记录，先向上聚合
python scripts/aggregate.py rollup --frm week --to month --client 青石峡漂流 --data-dir data
python scripts/aggregate.py rollup --frm week --to quarter --client 青石峡漂流 --data-dir data

# (c) 生成复盘报告（含 统计/对比/趋势/目标完成度 四类）
python scripts/aggregate.py review \
  --client 青石峡漂流 --type month --ref 2026-07-14 --completed \
  --data-dir data --targets config/targets.json --out reviews
```

`review` 子命令输出：
- `reviews/<客户>__<周期>.md`：五章节报告（概览 / 统计数据 / 对比数据(环比+同比) / 趋势分析 / 目标完成度）
- `reviews/<客户>__<周期>.csv`：扁平聚合数据，便于进表格/看板

四类数据定义、指标全集、周期日期规则、存储与聚合规则见 **`references/review-schema.md`**（本能力的权威数据模型）。

> 提示：对比的「同比」需要历史上同年同周期的记录；趋势需要历史上连续子周期记录。首次使用只有当期数据是正常的——把每周/每月的记录持续 `collect`，后续月/季/年复盘的对比与趋势会自动补全。

### 4.7 代运营商家全量采集（抖音林客 → 探索列表，2026-08-15 新增）

> 用途：**代运营公司一次拉出旗下全部代运营商家**在某时间窗的核销GMV / 退款GMV / 总预估佣金 / 服务商预估佣金（含衍生：核销率 / 退款率 / 推广佣金成本）。
> 与前面「生意经单商家复盘」互为补充：第 4.5 节看**单商家纵向**，本节看**跨商家横向 + 服务商成本测算**。

**前置**：Edge/Chrome 已登录 `life-partner.cn`（与管理「生意经」的 Chrome 是同一个，cookie 不同但同账号体系）。

**脚本**：`tools/extract_daiyunying.py`（已实现）
- 默认：服务中商家 + 近1个月（30天滚动窗）
- 支持子 tab：`--tab 全部商家 / 服务中商家 / 无忧核商家 / 新签商家 / 取关合作商家`
- 支持时间：`--period 近1个月|近7天|昨天|natural|custom`，后两者配合 `--y1 --m1 --d1 --y2 --m2 --d2`

```bash
# 1) 默认（服务中商家 + 近1个月）
python tools/extract_daiyunying.py

# 2) 自然月（2026-07），用户最常用
python tools/extract_daiyunying.py --period natural \
    --y1 2026 --m1 7 --d1 1 --y2 2026 --m2 7 --d2 31 \
    --out "代运营_2026-07.csv"

# 3) 全部商家（不限代运营状态）
python tools/extract_daiyunying.py --tab 全部商家 --period 近7天
```

**脚本自动做的事**：
1. `ld.LD(target_hint="life-partner")` — 复用 `ld.py`，仅 hint 不同（不创建并行客户端）
2. 导航：左菜单「商家数据」→ 顶部 tab「探索列表」
3. 设时间范围（`natural`/`custom` 走 `set_range`，复用生意经日历的 byted-date 双月面板打法）
4. 切子 tab（默认 服务中商家）
5. 检测分页（读「商家总数: N」+ 当前页码 + 每页大小），循环点「下一页」按钮（**真实鼠标**，React SPA 必备）
6. 读取每一行（按列名映射到标准英文键），衍生计算核销率/退款率/推广佣金成本
7. 输出 `out/代运营_<tab>_<period>.csv` + `.json`（原始备份，便于排查）

**典型输出列**（CSV 标准键）：`merchant_name / merchant_id / industry / cooperation_mode / category / business_score / pay_gmv / verified_gmv / refund_gmv / verified_medical_gmv / live_pay_gmv / total_est_commission / provider_est_commission` + 衍生 `_yuan`/`_num`/`verify_rate`/`refund_rate`/`promotion_cost_yuan`。

**已知踩坑 / 首次跑建议**：
- 必跑一次并把 `.json` 备份打开看 `headers`，确认 `provider_est_commission` 是否抓到（部分版本列在水平滚动区右侧）。
- 时间口径：「近1个月」≠ 自然月，跨月对比务必用 `--period natural --y1 --m1 ... --y2 --m2 ...` 显式锁定。
- 商家总数 > 100 时脚本会跑较久（每页 ~0.6s + 网络延迟），请勿中途重启 Edge。
- 完整字段定义、衍生公式、与生意经复盘的关系见 `references/modules.md` 第 9 节。

### 5. 收尾
- 多客户：回到商户选择弹窗 → 选下一家 → 重复步骤 2–4.5（**不要重启 Chrome**，保持登录态）。
- 全部完成后 `$AB close`。
- 向用户交付文件，简述本次取数范围、时间窗口、覆盖客户与字段含义。

## 常见模块速查
| 模块 | 真实位置 | 关键字段 |
|------|----------|----------|
| 经营概览 | life-data.cn 经营标签 | 成交金额、核销金额、退款、预约 |
| 流量来源 | life-data.cn 流量标签 | 总曝光、门店访问、直播/视频/搜索 各自成交/核销/转化率 |
| 内容分析 | life-data.cn 内容标签 | 直播时长、场次数、直播核销；视频播放、种草价值 |
| 人群资产 | life-data.cn 人群标签 | 新客/老客、复购率、人群画像 |
| 团购商品 | life.douyin.com 团购管理 | 在售商品、销量、收款、核销 |
| 订单与核销 | life.douyin.com 订单 | 订单号、状态、退款、核销时间 |
| 达人带货 | life.douyin.com 营销/精选联盟 | 达人、GMV、佣金、结算状态 |
| 评价管理 | life.douyin.com 评价 | 评分、评价内容、回复状态 |
| **代运营商家列表（2026-08-15 新）** | **life-partner.cn 商家数据→探索列表** | **支付/核销/退款GMV、总预估佣金、服务商预估佣金（差值=推广成本）** |

完整字段映射、四维度复盘字段、选择器提示见 `references/modules.md`；提取/启动/会话坑技巧见 `references/extraction.md`；**多维度复盘数据模型见 `references/review-schema.md`**；目标配置示例见 `config/targets.json.example`。

## 能力说明（实测，2026-07-15；Edge+Python CDP 方案更新于 2026-07-22；林客代运营采集新增于 2026-08-15）
已系统性整理为 **`references/capabilities.md`**，分两部分：
- **能做到的**：浏览器自动化读取、多商户切换、生意经+来客+直播专业版数据读取、**林客代运营全量商家采集（核销/退款/两列佣金 + 推广成本测算，2026-08-15 新）**、normalize 规整（JSON/HTML→CSV/Excel）、四维度复盘聚合（period/collect/rollup/review/query 五子命令 + 统计/对比/趋势/目标四类数据）、飞书文档交付。
- **不能做到的**：不能自动登录（会话 cookie 重启即丢）、**视频管理页无自然月键 / 直播专业版自然月实为30天滚动窗**（这两处日期框仍受限）、沙箱拦截 blob 下载（须翻页快照解析）、React SPA 交互须 eval dispatchEvent + IIFE、人群自然月仅首购数据、需持续 collect 才有历史对比/趋势。
  - **注**：生意经「自定义」日历**已自动化打通**（用户发截图教学），方法见 `references/user-taught-methods.md`，不再属于"不能做到"。
