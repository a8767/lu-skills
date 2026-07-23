# 抖音来客后台提取与分页技巧（agent-browser 版）

> 配合 `laiketui-data-reader` 与 `agent-browser` CLI 使用。核心：先用 `agent-browser snapshot` 拿 `@eN` 元素引用，再交互，再验证。

## 0. 调用约定
本环境 `agent-browser` 不在 PATH，用 node 调入口脚本并指定系统 Chrome：
```bash
export CHROME_PATH="C:/Users/Admin/AppData/Local/Google/Chrome/Application/chrome.exe"
AB="C:/Users/Admin/.workbuddy/binaries/node/versions/22.22.2/node.exe C:/Users/Admin/.workbuddy/binaries/node/workspace/node_modules/agent-browser/bin/agent-browser.js"
# 之后所有命令写成： $AB <子命令> ...
```

## 0.5 Windows 启动可连接的 Chrome（会话级 cookie 关键坑）
- **来客/生意经登录是会话级 cookie**：Chrome 一重启即被清除，磁盘上存的 cookie 无法在重启后的浏览器里恢复登录。**必须让用户当场在带调试端口的 Chrome 里登录一次**。
- 用 **PowerShell `Start-Process` 脱离 shell** 启动（实测：在 bash 里用 `&` 后台起，进程会被 shell 退出连带杀掉）：
  ```powershell
  Start-Process -FilePath "$env:USERPROFILE\AppData\Local\Google\Chrome\Application\chrome.exe" `
    -ArgumentList '--remote-debugging-port=9222','--remote-allow-origins=*',`
    "--user-data-dir=$env:USERPROFILE\AppData\Local\Google\Chrome\User Data",'--no-first-run'
  ```
- 验证端口监听：
  ```bash
  netstat -ano | grep ":9222"        # 应出现 LISTEN
  curl -s http://127.0.0.1:9222/json/version
  ```
- 连接后让用户在此窗口登录，再用 `$AB cookies get | grep -iE "sessionid|uid_tt|sid_tt"` 复核（有输出即已登录）。
- **取数期间不要重启该 Chrome**，否则会话 cookie 丢失需重新登录。
- 多 Profile：带空格的 `--profile-directory=Profile 98` 在 PowerShell 会被空格拆开（可改无空格 junction 规避）；但实测即便加载正确 Profile，会话 cookie 仍恢复不了，最终仍需当场登录。

## 1. 通用提取顺序
1. 建立会话：`$AB connect 9222`（连用户已登录 Chrome）或 `$AB open <url>`（新开并让用户登录）。
2. `$AB snapshot` → 看可访问树与 `@eN` 引用、当前 URL/标题。
3. 进入目标模块：`$AB click @eN`。
4. 设置筛选（日期/门店）。
5. 提取：优先 `$AB eval` 取结构化数组；表格复杂时用 `$AB get html "table"`。
6. 分页循环至末页。
7. `$AB close` 收尾。

## 2. 整表提取（推荐）
```bash
# 干净的结构化数组（直接喂给 normalize.py）
$AB eval "Array.from(document.querySelectorAll('table tbody tr')).map(r=>Array.from(r.children).map(c=>c.innerText.trim()))" > out/raw.json
```
把输出存为 `out/raw.json`（应为二维数组）。若页面有多个表，按模块逐一 eval 不同选择器，例如：
```js
// 只取第 2 个表格
document.querySelectorAll('table')[1].querySelectorAll('tbody tr')
```

## 3. 看板指标（非表格）
- 用 `$AB snapshot` 找到指标卡片的 `@eN`，再 `$AB get text @eN`。
- 或用 `$AB screenshot out/board.png` 后由多模态视觉直接读数字。
- 注意"万元""亿"单位，记录原始单位，交给 normalize.py 或人工换算。

## 4. 日期筛选
- 点击日期输入框引用 → `$AB fill @eN ""` 清空 → 输入 `YYYY-MM-DD` 或点击"近7天/昨日/本周"按钮引用 → 确认。
- 若日期是日历组件（非 input），用 `$AB click @eN` 逐层展开年月日再点选。
- 设置后用 `$AB snapshot` / `$AB screenshot` 确认时间范围已生效（页面常显示"2026-07-07 ~ 2026-07-13"）。

## 5. 门店筛选（多门店/连锁）
- 下拉：`$AB click @eN` 展开 → 从选项列表点选，或 `$AB select @eN "门店名"`。
- 搜索框：填入门店关键字后从联想列表点击。
- 连锁"全部门店"通常是一个复选/单选引用，优先确认其存在。

## 6. 分页处理
先定位分页区：
```bash
$AB get text @ePager        # 读"共 1234 条 / 第 1/62 页"
```
循环：
```bash
$AB click @eNext && $AB eval "..." >> out/page2.json
```
直到当前页 = 总页数或"下一页"禁用。把每页结果按顺序追加到同一 JSON 后再 normalize。

## 7. 反爬/动态加载注意
- 来客部分表格是异步加载：点击后先 `$AB wait "table tbody tr"` 或 `$AB wait 3000`，再提取。
- 若 `eval` 返回空，先 `$AB scroll down` 触发懒加载，再 `$AB snapshot`。
- 不要高频连续请求；翻页间可不加 sleep，但若遇限流，提示用户稍后重试。

## 8. 输出落盘约定
- 原始提取存到工作区 `out/` 目录（如 `out/raw_团购数据_2026-07-14.json`）。
- 规整后存 `out/laiketui_<模块>_<日期>.csv`（或 `.xlsx`）。
- 交付时向用户说明：取数时间窗口、覆盖门店、字段含义、单位。

## 9. 实测导航路径（life-data.cn 数据中心）
- `life.douyin.com` 首页 → 点**顶部导航「生意经」**（注意：不是左侧菜单里同名链接，那个只滚动首页）→ 跳转 `www.life-data.cn/...` 并弹出**商户选择弹窗**。
- 门店管理员账号：弹窗里搜索客户名（如「青石峡」）→ 选中 → 进入该客户的数据中心。**每家客户单独读取、单独导出（文件名带客户名）**。
- 数据中心默认显示"今天/近7天"。**日期选择有两套入口**：①图表区附近的「近7日/近30日/自定义」快捷选择器，仅支持 ≤1 个月范围；②**页面右上角的「自定义」**，可手动选 >1 个月的任意范围（月/季/年复盘必须用这个）。
- 周（≤7日）复盘：用快捷选择器或默认"近7天"即可。
- **月/季/年复盘**：自动化点击右上角「自定义」常因 React 合成事件弹不出日历，最稳妥做法是**请用户在右上角「自定义」手动设好起止日**（如月复盘选 06/01~06/30），设好后 agent 再读数据。设完用 `snapshot`/`screenshot` 确认页面显示的时间范围已生效。
- 顶部标签：首页 | 经营 | 流量 | 商品 | 人群 | 排版 | 行业竞争。
- 周复盘取数清单与各字段来源见 `modules.md` 第 6 节。

## 10. 四维度复盘：对比/趋势/目标 数据抓取

> 四维度复盘（周/月/季/年）除"统计数据"外，还需**对比、趋势、目标完成度**三类数据。抓取优先级：**优先用历史记录由 `aggregate.py` 自动算**，页面直读作为补充。

### 10.1 对比数据（环比/同比）
- **页面直读**：生意经多数看板有「对比」开关。打开后页面会显示"较上一周期 +x%"或"较去年同期 +x%"，用 `snapshot`/`get text` 读取各指标 delta。
- **脚本计算（推荐，免重复抓取）**：只要已 `collect` 了上一周期、及去年同周期的记录，`aggregate.py review` 会自动算出 `qoq_pct` / `yoy_pct`。缺失基准周期时该指标标 `—`，不臆造。
- 周期对照规则见 `modules.md` 第 7.2 节（环比=上一相邻周期；同比=去年同期）。

### 10.2 趋势分析
- **页面直读**：把日期范围拉到长窗口（月复盘拉 12 个月、年复盘拉 5 年），生意经趋势图/逐期明细表会展示子周期序列；用 `eval` 取图下表或趋势数据点。
- **脚本拼接（推荐）**：把每个子周期分别 `collect` 后，`aggregate.py review --type month --trend-count 12` 自动拼出最近 12 个月走势，无需一次抓取超长窗口。
- 趋势粒度与默认 N 见 `modules.md` 第 7.3 节。

### 10.3 目标完成度
- 目标值**不来自页面**，而在 `config/targets.json`（复制 `targets.json.example` 填写）。按 `客户 → 周期类型(week/month/quarter/year) → 指标键` 配置目标值。
- `aggregate.py review --targets config/targets.json` 自动算 `完成率% = 实际/目标`。未配置指标标"未设目标"。
- 维护建议：年目标可在年初设一次，月/季目标按需拆设；脚本暂不支持自动按年目标拆月，需人工在配置里写明各周期目标。

### 10.4 与 aggregate.py 的衔接
抓取到的本周期指标 → 写成 `data/<客户>/records/<key>.json`（用 `aggregate.py collect`）→ 再 `review` 出四类数据报告。历史记录越完整，月/季/年复盘的对比与趋势越丰满。
