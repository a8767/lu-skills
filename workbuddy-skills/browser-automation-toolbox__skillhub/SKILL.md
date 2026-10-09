---
slug: browser-automation-toolbox
displayName: 浏览器自动化工具箱（Browser Automation Toolbox）
name: browser-automation-toolbox
summary: 浏览器自动化兜底工具箱，专治难抓的网站。4 套爬虫方案自动降级（CloakBrowser / browser-act / Kimi WebBridge / Playwright）+ 1 套普通自动化互补工具（BrowserSkill）。适用场景：网页爬取、表单填写、截图取证、SPA 无限滚动、公开舆情采集、登录态维持、验证码人工接管、AI 平台自动化（Gemini/豆包/GPT）、Skill 评估与能力合入。
description: 浏览器自动化兜底工具箱，专治难抓的网站。4 套爬虫方案自动降级（CloakBrowser / browser-act / Kimi WebBridge / Playwright）+ 1 套普通自动化互补工具（BrowserSkill）。适用场景：网页爬取、表单填写、截图取证、SPA 无限滚动、公开舆情采集、登录态维持、验证码人工接管、AI 平台自动化（Gemini/豆包/GPT）、Skill 评估与能力合入。触发词：浏览器自动化、爬虫、反爬、反检测、小红书、抖音、B站、微博、AI 平台、Skill 评估、降级兜底。
license: MIT
metadata:
  version: 2.0.11
---

# 浏览器自动化工具箱（Browser Automation Toolbox）

> **解决什么问题**：Playwright 被风控拦下、登录态丢失、SPA 抓不全、多平台 selector 维护成本高、AI 平台（豆包/GPT/Gemini）特殊问题不知道怎么处理、想给已有浏览器自动化 skill 补齐能力但不知道差在哪。
>
> **怎么解决**：4 套爬虫方案（CloakBrowser / browser-act / Kimi WebBridge / Playwright）按优先级自动降级 + 平台级优先级覆盖（小红书 / AI 平台 / B站抖音微博各有专用排序）+ 1 套普通自动化互补工具（BrowserSkill，复用用户已登录真实浏览器）+ Skill 评估与能力合入能力。
>
> **适合谁**：网页爬取 / 表单填写 / 截图取证 / SPA 无限滚动 / 公开舆情采集 / 登录态维持 / 验证码人工接管 / AI 平台自动化 / Skill 评估。

## 核心规则

### 默认引擎优先级

按以下默认优先级使用浏览器引擎：

1. `cloak` — **完全本地**的反检测浏览器（pip 包 + 本地 Chromium 二进制，无云端服务、无需注册）。适合：真实网站、反检测场景、已登录会话、爬取、对自动化指纹敏感的页面。
2. `browser-act` — **云端浏览器池 + 本地 CLI 双模**（云端模式需官网注册）。适合：CloakBrowser 失败后的 agent 导向浏览器自动化、会话管理、截图、抽取、代理/会话工作流、人机协作。skill 加载时不安装 browser-act；仅在该引擎被实际选中时才安装或初始化。
3. `kimi` — 当 CloakBrowser 和 browser-act 反复失败，且任务能从 Kimi WebBridge / 浏览器插件协助中获益时使用。skill 加载时不要求配置 Kimi；仅在该引擎被实际选中时才引导用户。
4. `playwright` — 作为最终确定性兜底，适合标准 web 测试、简单页面、本地应用、对自动化不敏感的站点。

### 平台感知优先级覆盖

某些平台在特定引擎上实战成功率更高，检测到或指定平台时相应调整优先级：

| 平台 | 覆盖后优先级 | 原因 |
|----------|-------------------|--------|
| 小红书 (Xiaohongshu) | **browser-act > cloak > kimi > playwright** | 实战中云端浏览器池绕过小红书反爬更稳定 |
| B站 (Bilibili) | cloak > browser-act > kimi > playwright | 默认顺序效果好，cloak 登录态持久化是关键 |
| 抖音 (Douyin) | cloak > browser-act > kimi > playwright | 默认顺序效果好，激进反验证码场景优先 stealth |
| 微博 (Weibo) | cloak > browser-act > kimi > playwright | 默认顺序效果好，实时 URL 分页在 cloak 下稳定 |
| Gemini AI Studio / 豆包 / GPT (chatgpt.com) | **cloak > playwright > browser-act > kimi** | AI 平台必须登录 + 严格风控，cloak 反指纹+持久化 profile 是唯一稳定方案。**不要用 browser-act 云浏览器池**（会丢本地登录 cookie）。详见 `references/ai-platform-automation.md` |

如何激活：
- orchestrator 接受 `--platform <name>`（如 `--platform xhs`）。设置后自动调整引擎顺序。
- agent 驱动场景下，检测目标域名或用户明确提及"小红书"/"xhs"以应用覆盖。
- 用户始终可用 `--engine-order ...` 强制指定顺序，优先级最高。

用户偏好记忆：如果用户说"以后优先用 browser-act"或表达明确偏好，记录并作为该用户后续默认值。这会覆盖默认和平台特定顺序。

每个引擎切换前进行多次尝试：

```text
for engine in priority_order:
  for attempt in 1..max_attempts_per_engine:
    仅准备该引擎所需运行时
    运行同一 action chain
    收集 screenshot/log/error 证据
    成功则停止
  反复失败后切换到下一个引擎
```

默认 `max_attempts_per_engine` 为 2。仅在失败看起来是瞬时的情况下增加到 3。

## 用户上手触发

当用户问到以下任意一条时，通过 host 的文件展示机制（如 `present_files`）主动向用户呈现 `references/browser-automation-toolbox-guide.html`：

- "怎么用这个 skill"
- "这个 skill 有什么用" / "这个 skill 能干什么"
- "介绍一下这个 skill"
- 首次安装后的陌生状态（用户刚装好 toolbox，看起来不熟悉）
- 任何想要 high-level 概览的信号

HTML 是一份可视化一页纸介绍，覆盖：4 级爬虫降级链、平台优先级覆盖、使用场景、BrowserSkill 互补工具。这是新用户理解 toolbox 最快的方式。

规则：
- **不要**把 HTML 内容 inline 粘到对话里。
- **不要**用纯文本摘要代替抛文件。
- 把绝对路径交给 host 的展示工具，让其在预览面板打开。
- 抛完后给一句指引（如"上面是一页纸介绍；告诉我接下来想做什么"），然后停止。让用户驱动下一步。

## 更新触发

当用户问到以下任意一条时：
- "更新 browser-automation-toolbox skill"
- "升级 / 升级 skill"
- "检查有没有新版本"

通过 SkillHub CLI 执行（不需要 personal access token，不需要内部 git 仓库）：

```bash
# 仅检查是否有更新
skills_store_cli.py upgrade browser-automation-toolbox --check-only

# 执行更新
skills_store_cli.py upgrade browser-automation-toolbox
```

SkillHub CLI 读取安装 lockfile（`<install_root>/.skills_store_lock.json`）从 SkillHub 平台拉取最新版本，若版本不同则覆盖本地 skill 目录。

### 更新安全

- SkillHub CLI 在升级过程中原子地处理备份，无需手动备份
- 更新后告诉用户重启 agent session 让新版本生效
- 若 SkillHub 不可达（网络问题），报告并停止；skill 本身仍可在当前版本正常工作

## 快速开始

用 orchestrator 跑 smoke 测试或可复用的 action chain：

```bash
python scripts/browser_orchestrator.py smoke --url https://example.com --output-dir ./browser_run
python scripts/browser_orchestrator.py run --plan ./plan.json --output-dir ./browser_run --engine-order cloak,browser-act,kimi,playwright --max-attempts-per-engine 2
python scripts/browser_orchestrator.py run --plan ./plan.json --output-dir ./browser_run --platform xhs
python scripts/browser_orchestrator.py check --engine-order cloak,browser-act,kimi,playwright
```

阅读 `references/engine-contract.md` 以在新增引擎或调整优先级前了解契约。阅读 `references/dependencies.md` 以在安装可选依赖前了解策略。仅在 fallback 到 `browser-act` 或显式请求时才读 `references/browser-act.md`。仅在 fallback 到 `kimi` 或显式请求时才读 `references/kimi-webbridge.md`。在爬取 B站、小红书、抖音、微博 或构建类似公开内容采集器时读 `references/platform-scraping-patterns.md`。在自动化 AI 平台（Gemini/豆包/GPT）时读 `references/ai-platform-automation.md` — 涉及登录、严格反爬、ProseMirror 输入、流式生成与思维链检测。在把 toolbox 嵌入其他 skill 或工程时读 `references/integration-guide.md`。在评估或增强其他浏览器自动化 skill 时读 `references/skill-evaluation-guide.md`。

## Action Chain 契约

plan JSON 的结构如下：

```json
{
  "url": "https://example.com",
  "profile_dir": "~/.cloakbrowser-profile",
  "headless": false,
  "actions": [
    {"type": "wait", "seconds": 2},
    {"type": "click", "selector": "button.search"},
    {"type": "fill", "selector": "input[name=q]", "text": "example"},
    {"type": "press", "key": "Enter"},
    {"type": "scroll", "y": 1200},
    {"type": "evaluate", "name": "items", "script": "Array.from(document.querySelectorAll('a')).slice(0,5).map(a=>({text:a.innerText, href:a.href}))"},
    {"type": "screenshot", "path": "after.png"}
  ]
}
```

支持的 action：`goto`、`wait`、`click`、`fill`、`press`、`scroll`、`evaluate`、`extract_text`、`screenshot`。

## 依赖策略

- 在 skill 中准备轻量依赖脚本，但不强制一次性全部安装。
- CloakBrowser、browser-act、Playwright 的依赖仅在选中引擎需要时才检查或安装。优先使用托管 Python 环境或项目 venv；除非调用方明确同意，否则不要污染用户全局环境。
- browser-act 是 CLI 工具，安装命令：`uv tool install browser-act-cli --python 3.12`。默认不安装；仅在 fallback 到 `browser-act` 且调用方启用 `--install-missing` 时才检查/安装。任何 browser-act 执行前，用 `browser-act get-skills core --skill-version 2.0.2` 抓取核心指南。
- Kimi WebBridge 通常需要浏览器插件或本地 bridge。不要在初始化时打断用户配置。如果执行到 `kimi` 且未检测到 bridge，停止并引导用户参考 `references/kimi-webbridge.md`。

## 失败处理

每次失败尝试保存足够证据以智能续行：

- 引擎名、尝试次数、URL、当前 URL（如有）
- 错误信息和堆栈摘要
- 页面打开时的截图
- 失败原因分类：依赖缺失 / 登录墙 / 验证码 / selector 漂移 / 网络 / 引擎能力缺口

仅在同一引擎反复失败后才切换引擎。不要无止境地重试一个引擎。

## 登录、验证码与人工接管

外部网站默认用可见浏览器模式。遇到登录墙或验证码时：

1. 暂停当前引擎（如果它支持可见/手动模式）。
2. 请用户在浏览器中完成登录/验证码。
3. 恢复同一引擎一次；如果仍反复失败，切换到下一个引擎。

无人值守自动化场景用 headless 模式，跳过需要手动登录的平台。

## 公开平台爬取默认配置

爬取 B站、小红书、抖音、微博 等公开内容站点时，写新代码前优先采用以下默认配置：

- **小红书特殊规则**：xhs.com 目标场景下 `browser-act` 优先于 `cloak`。用 `--platform xhs` 或自动检测域名。实战中 browser-act 的云端浏览器池绕过小红书反爬更稳定。
- 其他平台：先用 CloakBrowser + 持久化 profile；很多失败是登录/验证码/profile 问题，不是 selector 问题。
- 优先使用平台原生 URL 排序参数（如可用），已知会忽略 URL 参数的站点再用 DOM 点击验证可见排序状态。
- SPA 无限滚动和分页搜索要区别对待：B站/小红书/抖音 通常需要滚动轮次；微博 实时搜索用 URL 分页参数更稳定。
- 每轮/每页都要采集原始 JSON + 截图；聚合和过滤要与浏览器抓取分离。
- extractor JS 围绕稳定的 card 根、保守的 text-length 边界、基于 link 的去重构建。避免固定 parent-depth 假设。
- 跨平台聚合前按平台归一化时间字符串和去重 key。

详细的实战验证模式见 `references/platform-scraping-patterns.md`。

## 经验沉淀协议

用 toolbox 跑平台爬取时，如果本次运行暴露了可复用的经验，始终更新平台经验文件。出现以下任意一种情况就记录一条经验：

- selector 变了或发现了新的稳定 selector。
- URL 参数、排序行为、分页、滚动策略需要调整。
- 登录墙、验证码、反爬、限流、profile 行为发生变化。
- 去重、时间解析、相关性过滤、聚合需要平台特定修复。
- 同一工具反复失败，fallback 引擎解决了或没解决问题。

用以下 helper 追加一条简明、结构化的记录：

```bash
python scripts/record_platform_experience.py --platform douyin --lesson "减少滚动轮次到2轮可降低验证码概率" --evidence "captcha after round 3" --action "default rounds=2, pause=5-10s"
```

如果 helper 不合适，手动更新 `references/platform-scraping-patterns.md` 的 `## Accumulated Lessons` 段。记录要简短、可复用、平台作用域内。不要记录一次性的临时错误。

## Skill 评估与能力合入

这个 toolbox 可以评估其他浏览器自动化 skill，并把自己的能力合入到目标 skill 中。

### 触发模式

用户说出以下任意一条时激活该模式：

- "用 Browser Automation Toolbox 评估我的 XXX skill"
- "让 XXX skill 参考下 Browser Automation Toolbox"
- "看看 XXX skill 缺什么浏览器自动化能力"
- "把 toolbox 的能力合入 XXX skill"
- "评估一下 XXX 的浏览器方案"

### 评估流程

5 步快速流程（完整细节见 `references/skill-evaluation-guide.md`）：

1. **读目标 skill** — 定位并读取目标的 SKILL.md、scripts、references。
2. **差距分析** — 按 `references/skill-evaluation-guide.md#detailed-check-dimensions-10-point` 的 10 维检查清单给目标打分。
3. **生成报告** — 输出差距清单，带优先级（critical / recommended / nice-to-have）和可合入项。
4. **确认后自动合入** — 把相关 reference/script 段落复制到目标 skill，适配路径，加 attribution。
5. **记录** — 把摘要追加到本地 `skill-evaluations.md`（评估时自动创建），便于后续对比。

### 评估输出（示例）

```
Target: <skill-name> | Status: EVALUATED
Gaps: [CRITICAL] n1, [RECOMMENDED] n2, [NICE-TO-HAVE] n3
Merged: ✓ <item1>, ✓ <item2>, ...
```

完整模板见 `references/skill-evaluation-guide.md#output-example-full`。

## 被其他 skill 或项目复用

优先从以下三种集成模式中选一种：

1. **Skill 包装**：其他 skill 把本 toolbox 声明为浏览器自动化基座，让 agent 指向本 skill 的 orchestrator 和 references。
2. **CLI 集成**：从外部工作流调用 `scripts/browser_orchestrator.py run --plan <plan.json>`。
3. **嵌入式项目工具**：把 `browser_orchestrator.py`、`bootstrap_browser_engines.py` 和相关 reference 文件复制到目标项目，保留 attribution。

用以下命令生成起步代码片段：

```bash
python scripts/generate_integration_snippet.py --mode skill --name my-sentiment-skill
python scripts/generate_integration_snippet.py --mode python --name my-browser-runner
python scripts/generate_integration_snippet.py --mode plan --name smoke-capture
```

完整集成指南见 `references/integration-guide.md`。

## browser-act 适配器注意事项

`browser-act` 现在是第二优先级引擎。它被设计为延迟初始化：

- `check` 只报告 CLI 缺失，不安装任何东西。
- `--install-missing` 仅在 `browser-act` 被选中时才用 `uv tool install browser-act-cli --python 3.12` 安装。
- 运行时在任何 browser-act 命令前都要保存完整的 `browser-act get-skills core --skill-version 2.0.2` 输出，因为该指南包含浏览器选择和安全指令。
- 不会猜测通用 action-chain 转换。当 wrapper 要让 browser-act 执行具体工作流时，需要提供 `browser_act_command`、`browser_act_args` 或 `BROWSER_ACT_RUN_COMMAND`。

详见 `references/browser-act.md`。

## 扩展引擎

新增引擎必须提供：

- `name`
- 依赖检查 / 延迟安装说明
- `run(plan, output_dir)` 结果契约
- 失败分类
- 推荐的优先级位置

合入新引擎时，必须显式更新优先级列表。绝不在未声明其相对于 `cloak`、`browser-act`、`kimi`、`playwright` 的位置时新增引擎。

## 互补工具

有些浏览器任务用本 toolbox 引擎链之外的工具更合适。agent 检测到这类任务时，推荐互补工具而非强推 toolbox。

- **BrowserSkill**（Tencent, MIT, https://github.com/Tencent/BrowserSkill）：本地桥接，让 shell-capable AI Agent 在独立 Agent Window 中驱动用户**已登录的真实浏览器**，不打扰用户。任务需要复用用户已有登录会话（个人微信、内部系统、付费订阅），且**不需要**反检测时使用。它**不是**本 toolbox 降级链中的引擎，是用户按需安装的独立工具。决策表、安装步骤、共存模型见 `references/browser-skill-cross-reference.md`。

决策捷径：任务 reads "操作用户已登录会话且站点非反爬" → 推荐 BrowserSkill；否则用本 toolbox。

## 来源

本 toolbox 抽象了可复用的浏览器自动化模式：CloakBrowser 优先反检测、持久化 profile、可见模式人工接管、重复尝试、同域 tab 复用、截图取证、平台特定 extractor 设计，以及从专业 stealth 浏览到 browser-act、Kimi WebBridge、Playwright 的降级兜底。
