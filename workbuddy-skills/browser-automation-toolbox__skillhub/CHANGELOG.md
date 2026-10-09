# Changelog

All notable changes to browser-automation-toolbox are documented here.
Versions follow semantic versioning: MAJOR.MINOR.PATCH.

## v2.0.11 — 2026-07-03

### Changed
- **SKILL.md 回滚到中文**：面向中文分发市场遵循中文规则。顶部新增「解决什么问题 / 怎么解决 / 适合谁」3 段中文概述，作为 SkillHub 详情页"概述"标签的第一屏门面。
- `displayName` 改为「浏览器自动化工具箱（Browser Automation Toolbox）」（去掉"兜底"二字，更简洁）。
- frontmatter 新增 `summary` 字段（SkillHub 可能优先显示 summary 而非 description）。
- 修复 1 处断链：`references/skill-evaluations.md` 改为「本地 skill-evaluations.md，评估时自动创建」（该文件是运行时生成的本地记录，不应作为 references 引用）。
- `metadata.version`: 2.0.10 → 2.0.11.

### Audit (skill-optimizer STOM)
- 行数：288 / 350（82%）✅
- 大小：16.88 KB / 15 KB（112%，超 1.88KB，中文字节膨胀导致，可接受）
- Frontmatter：7 字段全齐 ✅
- 引用链：12 个唯一 references，11 存在 + 1 断链已修复 ✅
- 综合评分：6.75/10 ⚠️ Bronze（建议优化但非必须）
- 决策：方案 A，不动大小（中文 skill 的 15KB 红线是软指标，SkillHub 无硬性限制）

## v2.0.10 — 2026-07-03

### Changed
- **SKILL.md 正文回滚到英文**：v2.0.9 把正文全部中文化其实超出了原意。SKILL.md 是面向 agent 的操作手册，英文更精确；面向用户的文案（description / displayName / README）保持中文。
- 保留 v2.0.9 的中文 frontmatter（slug / displayName / description / license）和中文 README。
- 保留 SkillHub CLI 的 Update Trigger 段（不回滚到 hot_reload.py）。
- `metadata.version`: 2.0.9 → 2.0.10.

### Rationale
面向用户的文案必须中文化（SkillHub 列表页 + 用户读的 README）；但 SKILL.md 正文是 agent 的操作手册，英文更精确，避免 agent 用英文理解再翻译成中文执行的损耗。

## v2.0.9 — 2026-07-03

### Changed
- **全文中文化**：SKILL.md 正文从英文改为中文（frontmatter 描述、触发条件、引擎说明、契约、经验沉淀、评估流程、复用模式、扩展规则等全部汉化）。
- `README.md` 新增「为什么需要这个工具箱？」段，列出 6 类用户痛点（Playwright 被风控 / 登录态丢失 / SPA 抓不全 / 多平台维护成本 / AI 平台特殊问题 / 现有 skill 能力不足），与 HTML 介绍文案保持一致。
- SKILL.md `description` 改为中文 + 触发词清单，提升 SkillHub 列表页可发现性。
- `displayName` 改为中文「浏览器自动化兜底工具箱」。
- `metadata.version`: 2.0.8 → 2.0.9.

### Rationale
面向 SkillHub 中文用户，英文摘要和英文 README 会降低可读性和可发现性。结合 HTML 已有的中文文案重写，避免生硬直译。

## v2.0.8 — 2026-07-03

### Added
- SkillHub distribution variant: removed `scripts/hot_reload.py` (SkillHub CLI handles upgrade natively via `skills_store_cli.py upgrade <slug>`), updated Update Trigger section to point to SkillHub CLI, scrubbed internal repo references from README.

### Changed
- `metadata.version`: 2.0.7 → 2.0.8.
- README install/update sections rewritten for SkillHub flow.

## v2.0.7 — 2026-06-29

### Added
- `references/ai-platform-automation.md`: AI 平台（Gemini / 豆包 / GPT）自动化经验专章。记录三平台真实 DOM 字段速查（豆包思维链/正文 selector、GPT 三 file input 区分、预览 src 格式、Gemini ms-autoscroll-container 等）、风控规避铁律、按平台图片上传策略、ProseMirror 输入、markdown 还原铁律、诊断套路（DOM dump 实证）、is_complete 完成检测策略、已验证场景、已知限制。
- `SKILL.md` Platform-Aware Priority Override 表格：新增 Gemini AI Studio / 豆包 / GPT (chatgpt.com) 行，引擎优先级 `cloak > playwright > browser-act > kimi`（**不要用 browser-act 云浏览器池**，会丢本地登录 cookie）。
- `SKILL.md` Quick Start 段 Read 引用：加 `references/ai-platform-automation.md` 触发条件说明。

### Changed
- `metadata.version`: 2.0.6 → 2.0.7.

### Scope note
本次合入严格限定为"3 平台自动化经验"，不含任何上游项目特定实现（架构、API 端点、版本号、内部 JS 命名等）。

## v2.0.6 — 2026-06-26

### Changed
- `README.md`: rewrote from English to Chinese. Migrated valuable content from `references/browser-automation-toolbox-guide.html` (4-tier fallback table, platform override, fallback strategy, BrowserSkill complementary tool decision table, usage scenarios).
- `metadata.version`: 2.0.5 → 2.0.6.

### Added
- README now serves as a standalone overview (no need to open the HTML for basic understanding).

## v2.0.5 — 2026-06-26

### Changed
- `scripts/hot_reload.py`: rewrote to use `git clone --depth 1 --filter=blob:none --sparse` instead of API v3. **No personal access token needed anymore** — same auth path as initial install (system credentials).
- Removed all token-related code: `--set-token` command, token load/save/guide/test, `.env.local` storage, API v3 HTTP layer.
- Reduced hot_reload.py from ~470 lines to ~300 lines.

### Removed
- `.env.local` from protected patterns and `.gitignore` (no longer used).
- `--set-token` command line option.
- Token setup guide (no longer needed).

## v2.0.4 — 2026-06-26

### Added
- `scripts/hot_reload.py`: skill self-updater with multiple modes (update / check-only / daily-check / rollback / set-token).
- `## Update Trigger` section in SKILL.md: natural-language triggers for update / rollback.
- `.gitignore`: excludes `.installed.json`, `.env.local`, `.last_check`, `__pycache__/`, `*.skill`, `*.zip`.
- `CHANGELOG.md`: this file (backfilled to v2.0.0).
- `README.md`: one-pager with install + update + rollback commands.
- Backup-and-rollback mechanism: 1 backup kept at `<sibling>/.backup/<skill-name>/`.
- B-mode update confirmation: shows CHANGELOG diff and asks user before overwriting.
- Token setup guide (interactive + non-interactive paths).
- Auto-detect skill install path (no hardcoded home dir); works across WorkBuddy / OpenClaw / CodeBuddy / Cursor / Claude Code / Codex / Pi / Hermes Agent.
- Credentials stored at `<skill-dir>/.env.local` (protected from overwrite, portable across harnesses).

### Changed
- `--daily-check` defaults to silent operation: 0 output when no token / no network / already checked today / already latest. Only emits a one-liner when an update actually happens.
- `metadata.version`: 2.0.3 → 2.0.4.

## v2.0.3 — 2026-06-26

### Added
- `references/browser-automation-toolbox-guide.html`: visual one-pager for onboarding.
- `## User Onboarding Trigger` section in SKILL.md: agent proactively presents the HTML when user asks "how to use / what does this skill do / first-time install".
- Explicit "do not inline HTML content" rule to prevent agent from summarizing instead of presenting the file.

## v2.0.2 — 2026-06-26

### Added
- `references/browser-skill-cross-reference.md`: BrowserSkill (Tencent/MIT, https://github.com/Tencent/BrowserSkill) as a complementary tool, not an engine.
- `## Complementary Tools` section in SKILL.md: decision shortcut for when to recommend BrowserSkill vs this toolbox.
- BrowserSkill is NOT in the fallback chain; it is an independent tool the user installs on demand.

## v2.0.1 — 2026-06-23

### Fixed
- CloakBrowser description in SKILL.md L16: clarified "fully local (pip package + local Chromium binary, no cloud service or registration)" — resolves agent misunderstanding where cloak was skipped because it was mistaken for a cloud service.
- browser-act description in SKILL.md L17: clarified "cloud browser pool + local CLI dual mode (cloud mode requires official site registration)" — forms explicit contrast with cloak.

## v2.0.0 — 2026-06-22

### Added
- Skill evaluation and enhancement capability: 10-dimension gap analysis + auto-merge with user confirmation.
- `references/skill-evaluation-guide.md`: full evaluation protocol, dimensions, gap report template, output example, auto-merge rules.
- `references/integration-guide.md`: 3 integration modes (skill wrapper / CLI / embedded project utility) + snippet generator.
- `scripts/generate_integration_snippet.py`: generates skill / python / plan snippets for downstream consumers.
- `scripts/record_platform_experience.py`: appends platform-specific lessons to `references/platform-scraping-patterns.md`.

### Changed
- Engine priority: `cloak > browser-act > kimi > playwright` (browser-act promoted to 2nd priority).
- Platform-aware priority override: `--platform xhs` flips to `browser-act > cloak > kimi > playwright`.

### Removed
- Old `browser-automation-base` package (replaced by `browser-automation-toolbox`).
