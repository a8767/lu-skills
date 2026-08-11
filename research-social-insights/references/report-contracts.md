# 报告契约

所有字段只写真实值。无法可靠得到时保持缺失、降低状态并在边界说明；不得写示例数字、默认平台或假标题。

## 风向扫描报告

```markdown
---
type: social-trend-report
schema_version: 1
status: complete
created: YYYY-MM-DD
updated: YYYY-MM-DD
title: 最近 7 天 AI 风向扫描
captured_at: YYYY-MM-DDTHH:mm:ss+08:00
timezone: Asia/Shanghai
time_window:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
scope: AI
depth: standard
privacy_level: deidentified
---

# 最近 7 天 AI 风向扫描

> [!summary] 一句话结论
> 一句话概括最重要的行动变化和证据边界。

## 扫描范围

- 时间：...
- 来源：...
- 判断口径：...

## 风向簇

| 风向编号 | 主题 | 大家在做什么 | 为什么现在 | 阶段 | 讨论分支 | 主要声音 | 需求与摩擦 | 独立来源数 | 覆盖平台 | 证据强度 |
|---|---|---|---|---|---|---|---|---:|---|---|

## 来源覆盖

| 来源类型 | 来源 / 平台 | 内容样本 | 评论 / 回复节点 | 主要用途 |
|---|---|---:|---:|---|

## 重点证据

| 证据编号 | 风向编号 | 脱敏表达 | 类型 | 来源 / 平台 | 发布时间 |
|---|---|---|---|---|---|

## 证据边界与已排除内容

- ...

## 私有来源索引

> [!warning] 仅用于本地复查
```

`讨论分支` 和 `主要声音` 用简短的分号分隔内容，不用未经定义的百分比。阶段只用：萌芽、扩散、分化、回落、持续、单点信号。

## 主题深挖报告

主题报告必须兼容 Workbench 现有 `social-insight-report` schema 1。Frontmatter 必填：

```yaml
type: social-insight-report
schema_version: 1
status: complete
created: YYYY-MM-DD
updated: YYYY-MM-DD
title: <研究标题>
topic: <主题>
research_question: <主研究问题>
research_type: cross-platform-snapshot
captured_at: YYYY-MM-DD
timezone: Asia/Shanghai
primary_platform: <主要社媒平台>
auxiliary_platforms: []
search_terms: []
privacy_level: deidentified
sample:
  search_results: {}
  visible_comment_reply_nodes: {}
  analysis_usable_comment_reply_units: {}
```

必需章节：

- `## 样本概览`：列为平台、角色、搜索结果样本、可见评论 / 回复节点、纳入分析、主要用途。
- `## 一页结论`：使用三级标题逐条展开。
- `## 评论区需求地图`：需求簇、用户想完成的任务、可见证据、常见失败、置信度。
- `## 观点阵营`：阵营、核心判断、代表证据、盲点。
- `## 一级评论与二级回复`：一级评论中的问题、二级回复带来的信息、研究价值。
- `## 跨平台差异`：平台、主导表达、评论区的信号、本轮局限。
- `## Workbench 可视化指标`：至少 3 个真实、可解释的 1–5 分指标；没有足够证据时状态降级，不能为了通过校验而补分。
- `## 脱敏证据摘录`：证据编号、脱敏表达、类型、所在平台。
- `## 证据边界与已排除内容`。

可选章节：研究问题、可继续验证的内容问题、私有来源索引、后续重复研究建议。

