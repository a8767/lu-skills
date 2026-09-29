# Codex skills

本目录是从一台 Windows 电脑整理的 Codex 用户级 skills 快照，盘点日期：2026-09-29。

- 共 **68 个顶层技能文件夹**，包含 **74 个 `SKILL.md` manifest**。
- 额外 6 个 manifest 是 viral-topic 下的平台专题 skill，以及 shadowbot-cli 的 macOS/信创变体。

## 安装

克隆仓库后，把本目录下含有 `SKILL.md` 的技能文件夹复制到 Codex 的用户级技能目录：

- Windows: `%USERPROFILE%\.agents\skills\` 或 `%USERPROFILE%\.codex\skills\`
- macOS/Linux: `~/.agents/skills/` 或 `~/.codex/skills/`

PowerShell 示例（在仓库根目录执行）：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills" | Out-Null
Get-ChildItem .\codex-skills -Directory | Copy-Item -Destination "$env:USERPROFILE\.agents\skills" -Recurse -Force
```

## 复制 skills 到本地的提示词

下面这段提示词可直接交给 Codex，用于把指定技能或全部技能复制到当前电脑：

```text
请从 GitHub 仓库 https://github.com/a8767/lu-skills 的 codex-skills/ 目录，把【填写 skill 名称；如需全部则写“全部”】复制到本机 Codex 用户级技能目录。

根据当前系统选择目标目录：
- Windows：%USERPROFILE%\.agents\skills\
- macOS/Linux：~/.agents/skills/

保留技能文件夹结构，以及技能依赖的脚本、参考文档和资源。不要复制内置技能、缓存、评测夹具或 .env 文件。复制前检查目标目录是否已有同名技能；不要直接覆盖，先列出冲突并等我决定。完成后核对每个技能的 SKILL.md 和资源文件，报告复制的技能名称、目标路径及冲突或失败项。
```

如果要装进 Codex 的另一种用户级目录，也可以把目标路径改为 `%USERPROFILE%\\.codex\\skills\\` 或 `~/.codex/skills/`。

## 清理规则

- 只收录个人级技能；内置 `.system` 与插件缓存不复制。
- `.agents/skills` 和 `.codex/skills` 下 28 份完全相同的 Firecrawl 技能只保存一份。
- 排除 Python 缓存、旧时间戳备份、评测夹具和 `.env` 文件；运行所需的脚本、参考文档和资源保留。
- 4 张约 5 MB 的诗经纸刊示例图已压缩为 JPEG，技能内引用已同步更新。Darwin 技能的展示动画未收录。

## 技能名单

- [ai-article-daily](./ai-article-daily/SKILL.md)
- [aihot](./aihot/SKILL.md)
- [apimart-image-gen](./apimart-image-gen/SKILL.md)
- [bilibili-viral-topic](./viral-topic/bilibili-viral-topic/SKILL.md)
- [book-illustration-workflow](./book-illustration-workflow/SKILL.md)
- [browser-skill](./browser-skill/SKILL.md)
- [china-ecommerce-analytics](./china-ecommerce-analytics/SKILL.md)
- [cover-skill](./cover-skill/SKILL.md)
- [darwin-skill](./darwin-skill/SKILL.md)
- [dingtalk-aisearch](./dingtalk-aisearch/SKILL.md)
- [dingtalk-aitable](./dingtalk-aitable/SKILL.md)
- [dingtalk-calendar](./dingtalk-calendar/SKILL.md)
- [dingtalk-chat](./dingtalk-chat/SKILL.md)
- [dingtalk-contact](./dingtalk-contact/SKILL.md)
- [dingtalk-doc](./dingtalk-doc/SKILL.md)
- [dingtalk-drive](./dingtalk-drive/SKILL.md)
- [dingtalk-event](./dingtalk-event/SKILL.md)
- [dingtalk-mail](./dingtalk-mail/SKILL.md)
- [dingtalk-minutes](./dingtalk-minutes/SKILL.md)
- [dingtalk-misc](./dingtalk-misc/SKILL.md)
- [dingtalk-shared](./dingtalk-shared/SKILL.md)
- [dingtalk-todo](./dingtalk-todo/SKILL.md)
- [dingtalk-wiki](./dingtalk-wiki/SKILL.md)
- [firecrawl](./firecrawl/SKILL.md)
- [firecrawl-agent](./firecrawl-agent/SKILL.md)
- [firecrawl-company-directories](./firecrawl-company-directories/SKILL.md)
- [firecrawl-competitive-intel](./firecrawl-competitive-intel/SKILL.md)
- [firecrawl-crawl](./firecrawl-crawl/SKILL.md)
- [firecrawl-dashboard-reporting](./firecrawl-dashboard-reporting/SKILL.md)
- [firecrawl-deep-research](./firecrawl-deep-research/SKILL.md)
- [firecrawl-demo-walkthrough](./firecrawl-demo-walkthrough/SKILL.md)
- [firecrawl-developer-index](./firecrawl-developer-index/SKILL.md)
- [firecrawl-download](./firecrawl-download/SKILL.md)
- [firecrawl-interact](./firecrawl-interact/SKILL.md)
- [firecrawl-knowledge-base](./firecrawl-knowledge-base/SKILL.md)
- [firecrawl-knowledge-ingest](./firecrawl-knowledge-ingest/SKILL.md)
- [firecrawl-lead-gen](./firecrawl-lead-gen/SKILL.md)
- [firecrawl-lead-research](./firecrawl-lead-research/SKILL.md)
- [firecrawl-map](./firecrawl-map/SKILL.md)
- [firecrawl-market-research](./firecrawl-market-research/SKILL.md)
- [firecrawl-monitor](./firecrawl-monitor/SKILL.md)
- [firecrawl-parse](./firecrawl-parse/SKILL.md)
- [firecrawl-qa](./firecrawl-qa/SKILL.md)
- [firecrawl-research-index](./firecrawl-research-index/SKILL.md)
- [firecrawl-research-papers](./firecrawl-research-papers/SKILL.md)
- [firecrawl-scrape](./firecrawl-scrape/SKILL.md)
- [firecrawl-search](./firecrawl-search/SKILL.md)
- [firecrawl-seo-audit](./firecrawl-seo-audit/SKILL.md)
- [firecrawl-shop](./firecrawl-shop/SKILL.md)
- [firecrawl-website-design-clone](./firecrawl-website-design-clone/SKILL.md)
- [firecrawl-workflows](./firecrawl-workflows/SKILL.md)
- [harness-engineering-claude](./harness-engineering/SKILL.md)
- [hv-analysis](./hv-analysis/SKILL.md)
- [hy-3d-gen](./hy-3d-gen/SKILL.md)
- [khazix-writer](./khazix-writer/SKILL.md)
- [leader](./leader/SKILL.md)
- [multi-agent-image](./multi-agent-image/SKILL.md)
- [neat-freak](./neat-freak/SKILL.md)
- [reshape-your-life](./reshape-your-life/SKILL.md)
- [scroll-promo-site-builder](./scroll-promo-site-builder/SKILL.md)
- [shadowbot-cli-macos](./shadowbot-cli/mac/SKILL.md)
- [shadowbot-cli-windows](./shadowbot-cli/SKILL.md)
- [shadowbot-cli-xinchuang](./shadowbot-cli/%E4%BF%A1%E5%88%9B/SKILL.md)
- [shijing-paper-zine](./shijing-paper-zine/SKILL.md)
- [storage-analyzer](./storage-analyzer/SKILL.md)
- [storefront-to-brand-system](./storefront-to-brand-system/SKILL.md)
- [task-harness](./task-harness/SKILL.md)
- [twitter-monitor](./twitter-monitor/SKILL.md)
- [video-downloader](./video-downloader/SKILL.md)
- [viral-title](./viral-title/SKILL.md)
- [viral-topic](./viral-topic/SKILL.md)
- [wechat-viral-topic](./viral-topic/wechat-viral-topic/SKILL.md)
- [x-viral-topic](./viral-topic/x-viral-topic/SKILL.md)
- [youtube-viral-topic](./viral-topic/youtube-viral-topic/SKILL.md)

本仓库是公开仓库。添加技能时请勿提交真实凭据、个人数据或其他不适合公开的信息。