---
name: research-social-insights
description: 主动研究近期中文 AI 社媒风向，或围绕一个指定主题深挖国内中文平台的讨论、一级评论、二级回复、观点阵营、需求、痛点与新闻背景。用户问“最近大家都在做什么/聊什么”、要求扫描中文社媒近况、研究某个国内社媒话题、分析评论区声音，或 Workbench 交接风向扫描与主题深挖任务时使用。
---

# Research Social Insights

## 目标

把公开中文网页和用户已授权登录后可见的中文社媒页面，整理成可复查的本地研究报告。此 Skill 只在用户主动触发时运行，不创建定时任务，不让 Workbench 保存平台登录态，也不自动生成选题。

先确定目标知识库根目录。优先使用用户明确提供的路径，其次读取 `PERSONAL_DASHBOARD_VAULT_ROOT`。仍无法确定时先询问用户，不猜测用户名、主目录或知识库名称。目标目录必须允许创建 `10_raw/social-insights/`。

开始时必须明示：本次模式、时间范围、将实际读取的来源类型、最终产出位置和下一步。结束时说明真实覆盖、未能可靠读取的来源、结论边界和报告路径。

## 两种模式

根据用户目的只选择一种模式：

1. `trend-scan`：回答“最近大家都在干什么、聊什么、争什么”。同义触发包括近期风向、趋势雷达、最近 7 天 AI 圈在做什么、哪些主题突然变多。完整流程见 [trend-scan.md](references/trend-scan.md)。
2. `topic-deep-dive`：围绕一个明确主题研究延伸子题、观点阵营、评论与回复、需求、痛点、反例和新闻背景。完整流程见 [topic-deep-dive.md](references/topic-deep-dive.md)。

“刷新”只是用新的捕获时间重新运行同一模式，不是第三种模式。若意图仍不明确，默认：有明确主题用 `topic-deep-dive`；否则用 `trend-scan`，范围为 AI，时间窗为最近 7 天，深度为标准。

## 固定执行流程

### 1. 确认任务合同

若目标知识库存在 `AGENTS.md`，先读取并遵守。然后从用户指令提取：

- 模式；
- 主题或范围；
- 研究问题；
- 时间窗；
- 深度：快速、标准或深度；
- 用户点名的平台或来源。

Workbench 生成的交接文本是任务输入，不代表已执行。不得声称 Workbench 已提交、后台已运行或结果已生成。

### 2. 制定查询与来源计划

先把主题拆成实体、动作、问题、别称、反向表达和相邻概念，再选来源。来源分工与读取边界见 [source-policy.md](references/source-policy.md)。至少区分：

- 国内官方或一手事实来源；
- 国内科技新闻与中文行业报道；
- 国内中文社媒内容；
- 一级评论与二级回复。

对近期事实和产品变化优先联网核实，并优先使用 [source-policy.md](references/source-policy.md) 列出的中文来源。公开网页使用当前 Agent 可用的网络搜索与打开能力；需要登录或交互才能读取的国内社媒页面，在 macOS 上使用 Ego Lite 提供的 `ego-browser`，复用用户已有登录态。不得尝试绕过登录、验证码、反爬或访问权限。

Ego Lite 当前不支持 Windows 或 Linux。在这些平台上使用可靠的中文公开网页，将缺少的登录态社媒覆盖写进证据边界，并把报告状态按实际质量降为 `partial` 或 `needs-review`；不得声称完成了完整的跨平台登录态扫描。

国内平台职责、来源分工、Ego Lite 登录态复用、独立来源判定、转载去重、代表性边界与失败降级统一以 [source-policy.md](references/source-policy.md) 为真源。`trend-scan` 的发现顺序、候选门槛、深度档位和时间序列用词边界统一以 [trend-scan.md](references/trend-scan.md) 为真源，不在 Workbench 交接文本或其他运行入口复制这些策略。

### 3. 收集与留痕

中间抓取、临时截图、候选列表和解析文件放在系统临时目录。只有最终报告写入 `10_raw/social-insights/`。不要把浏览缓存、低价值候选或失败页面长期写进 Vault。

可靠读取失败的内容不进入结论，不推测正文、评论或回复。只在证据边界中记录失败的来源类型和排除原因。昵称、头像、用户 ID、地区和其他可识别个人信息默认不进入报告。

### 4. 分析

遵循 [comment-analysis.md](references/comment-analysis.md) 和 [quality-gates.md](references/quality-gates.md)：

- 事件、行动和讨论分开；
- 事实、用户观点、作者观点、AI 综合推论分开；
- 一级评论和二级回复保持链路；
- 聚类后保留反方、小众声音和内部冲突；
- 不把互动量等同支持率，不把可见评论当总体民意；
- “趋势”必须有时间变化或多源趋同证据；只有单次横截面时写“当前风向”。

### 5. 写报告

严格使用 [report-contracts.md](references/report-contracts.md)：

- `trend-scan` 写 `type: social-trend-report`；
- `topic-deep-dive` 写 `type: social-insight-report`；
- `schema_version: 1`；
- `privacy_level: deidentified`；
- 状态只用 `complete`、`partial` 或 `needs-review`。

目录命名：

- 风向扫描：`10_raw/social-insights/YYYYMMDD-AI风向扫描/近期风向.md`
- 主题深挖：`10_raw/social-insights/YYYYMMDD-<中文主题>/社媒话题研究.md`

若同日同目录已存在报告，不覆盖旧证据；使用语义后缀或更新时间生成新文件。

### 6. 校验再交付

运行：

```bash
python3 <本 Skill 目录>/scripts/validate_report.py <报告绝对路径> --vault <知识库根目录>
```

校验失败时先修复。不能满足的关键字段保持显式缺失并把状态降为 `partial` 或 `needs-review`，不得填充占位数据或虚构样本。

## 输出边界

- 本 Skill 的最终产物停留在 Raw 证据层；不写 Wiki、`40_topics/`、`50_scripts/` 或账号数据层。
- 不把研究问题自动变成内容选题、待拍队列、商业建议或产品结论。
- 用户随后明确要求沉淀 Wiki 或开始内容制作时，再交回 `$media-content-wiki` 并遵守相应门禁。
- 只读本轮授权范围内的来源。用户点名但不可访问的平台，记录边界后继续使用可用来源，不伪装为已覆盖。
