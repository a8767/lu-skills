---
name: laiketui-data-reader
description: 读取抖音来客（life.douyin.com 商家后台）及其「生意经」数据中心（life-data.cn）的经营数据，支持门店管理员账号在多客户间切换读取。覆盖经营概览、流量（直播/视频/搜索）、内容分析、人群资产、团购、订单、达人分账、评价。通过浏览器自动化复用用户真实登录态，登录后抓取指标并导出为 CSV/Excel/复盘报告。支持周/月/季/年四维度复盘（统计/对比/趋势/目标完成度）。当用户要查来客后台数据、导出团购/核销明细、看经营看板、做本地生活经营复盘/周报/月报/季报/年报取数时使用。
version: 1.4.0
agent_created: true
display_name: "来客后台数据读取"
display_name_en: "Laiketui Data Reader"
description_zh: "读取抖音来客/生意经数据中心经营数据（支持多客户切换 + 周/月/季/年四维度复盘），浏览器自动化复用登录态并导出。"
description_en: "Read Douyin Laiketui merchant backend & 生意经 (life-data.cn) data, supports multi-merchant switching and weekly/monthly/quarterly/yearly review, export to CSV/Excel."
visibility: "private"
---

# 抖音来客后台数据读取（Laiketui Data Reader）v1.4.0

## 用途
通过浏览器自动化读取「抖音来客」商家后台及其「生意经」数据中心的经营数据，把抓取到的指标整理成 CSV/Excel/**多维度复盘报告**。

**重要**：本 skill 经真实实测跑通（2026-07-14，青石峡漂流门店管理员账号），以下流程为已验证路径。

## 何时使用
- 用户要查/导出抖音来客后台任何经营数据（GMV、核销、订单、退款、达人分账等）。
- 用户说"看经营看板""导出团购明细""统计核销率""拉达人带货数据"。
- 用户要做经营复盘/分析报告，且明确了**周期**：**周复盘 / 月复盘 / 季复盘 / 年复盘**。
- 用户是**门店管理员账号、下挂多家客户**（如代运营公司）：需在多家客户之间切换读取、分别导出（文件名带客户名）。
- 用户在做本地生活项目（团购、文旅、餐饮、加油站等）的对账或数据复盘。

## 前置依赖（本机已验证可用）
- **引擎 = `agent-browser`**（Rust CDP 浏览器自动化 CLI，本地已装，实测可打开来客页）。
  - 本环境它**不在 PATH**，调用方式：用 node 直接跑入口脚本，并指定系统 Chrome：
    ```bash
    AB="$NODE $AGENT_BROWSER_JS"   # $NODE=node 路径, $AGENT_BROWSER_JS=agent-browser 入口脚本路径
    export CHROME_PATH="$USERPROFILE/AppData/Local/Google/Chrome/Application/chrome.exe"
    ```
- **`browser-use` CLI 在本环境未安装**（仅装了说明文档）。本书面以 agent-browser 为准。
- 用户**必须已在其 Chrome 登录过来客后台**（手机号验证码）。本技能**不自动输入账号密码/验证码**，只复用已有登录态。
- **聚合引擎 = `scripts/aggregate.py`**（纯标准库 Python），用于四维度复盘的统计/对比/趋势/目标完成度计算与报告生成。

## 核心原则（含实测踩坑）
1. **来客登录是「会话级 cookie」——Chrome 一重启就失效**：实测确认，来客/生意经的登录会话 cookie（`sessionid_*`、`uid_tt_*`、`sid_tt_*`）在关闭 Chrome 后即被清除，**磁盘上存的 cookie 无法在重启后的浏览器里恢复登录**。
   - **正确做法**：用带调试端口的 Chrome **让用户当场登录一次**，登录后保持该 Chrome 开启、期间不要重启，本会话内直接取数。
2. **复用登录态，绝不自动登录**：只能复用用户真实 Chrome 的会话，不能自动填验证码或账号密码。
3. **先 snapshot 后操作**：每次交互前 `$AB snapshot` 拿 `@eN` 元素引用，操作后立刻 `snapshot`/`screenshot` 验证。
4. **只读取，不修改**：默认不做上架/改价/退款等写操作；用户明确要求时二次确认后再执行。
5. **入口先确认**：导航文案可能随版本调整，首次进入若路径不符，先用 `snapshot`/`screenshot`/`get url` 确认当前页面。

## 流程

### 0. 启动可连接的 Chrome（让用户当场登录——最关键一步）
来客数据登录后才能看。来客会话 cookie 重启即丢，所以流程是：**开一个带调试端口的 Chrome → 让用户在这个窗口里登录 → 连接取数 → 期间不重启**。

**用 PowerShell `Start-Process` 脱离 shell 启动**（实测关键：在 bash 里用 `&` 后台起会被 shell 退出连带杀掉；PowerShell 启动则独立存活）：
```powershell
Start-Process -FilePath "$env:USERPROFILE\AppData\Local\Google\Chrome\Application\chrome.exe" `
  -ArgumentList '--remote-debugging-port=9222','--remote-allow-origins=*',`
  "--user-data-dir=$env:USERPROFILE\AppData\Local\Google\Chrome\User Data",'--no-first-run'
```
> 多 Profile 注意：`--profile-directory=Profile 98` 在 PowerShell 里空格会被拆开（可改无空格 junction 规避）；但实测即便加载正确 Profile，会话 cookie 仍恢复不了，最终仍需用户当场登录一次。

启动后等约 7 秒，验证端口监听：
```bash
netstat -ano | grep ":9222"     # 应看到 LISTEN
curl -s http://127.0.0.1:9222/json/version   # 应返回 Chrome 信息
```

然后连接，并**让用户在此 Chrome 窗口内完成来客登录**（手机号+短信验证码，勾选协议框）。登录后复核：
```bash
$AB connect 9222
$AB open "https://life.douyin.com/"
# 用 cookies get 复核：出现 sessionid_*/uid_tt_*/sid_tt_* 即已登录
$AB cookies get | grep -iE "sessionid|uid_tt|sid_tt|odin_tt"
```

### 1. 进入「生意经」数据中心（实测路径）
- 进入 `life.douyin.com` 首页后，**点击顶部导航栏的「生意经」**（不是左侧菜单里同名的链接——侧栏同名链接只滚动首页）。
- 点击后 URL 跳转到 `www.life-data.cn/...`，并弹出**商户选择弹窗**。

**多客户管理员切换（核心场景）**：
- 弹窗列出当前账号可进入的所有商户。
- 在弹窗搜索框输入客户名（如「青石峡」）快速定位 → 选中 → 进入该客户的数据中心。
- **每家客户单独读取、单独导出**，文件名带客户名。

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
- 点「自定义」→ 弹出双月日历 → 点选起始日与结束日 → 点空白处/Esc 关闭日历。
  - **精确自动化操作（用户发截图亲授，2026-07-15）**：见 `references/user-taught-methods.md` 方法一——点统计周期旁的**日历图标**（非文本）→ 快捷选项「自定义」→ 双月面板中**日期格子有 `@eN` ref 可直接 `$AB click`** → 选起止 → 确认。跨月先选开始月日、再选结束月日。
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

提取方式：
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

完整字段映射、四维度复盘字段、选择器提示见 `references/modules.md`；提取/启动/会话坑技巧见 `references/extraction.md`；**多维度复盘数据模型见 `references/review-schema.md`**；目标配置示例见 `config/targets.json.example`。

## 能力说明（实测，2026-07-15）
已系统性整理为 **`references/capabilities.md`**，分两部分：
- **能做到的**：浏览器自动化读取、多商户切换、生意经+来客+直播专业版数据读取、normalize 规整（JSON/HTML→CSV/Excel）、四维度复盘聚合（period/collect/rollup/review/query 五子命令 + 统计/对比/趋势/目标四类数据）、飞书文档交付。
- **不能做到的**：不能自动登录（会话 cookie 重启即丢）、**视频管理页无自然月键 / 直播专业版自然月实为30天滚动窗**（这两处日期框仍受限）、沙箱拦截 blob 下载（须翻页快照解析）、React SPA 交互须 eval dispatchEvent + IIFE、人群自然月仅首购数据、需持续 collect 才有历史对比/趋势。
  - **注**：生意经「自定义」日历**已自动化打通**（用户发截图教学），方法见 `references/user-taught-methods.md`，不再属于"不能做到"。
