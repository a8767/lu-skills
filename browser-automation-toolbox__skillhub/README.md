# 浏览器自动化工具箱（Browser Automation Toolbox）

浏览器自动化兜底工具箱，专治难抓的网站。**爬虫 4 套方案 + 普通自动化 1 套互补工具**，平台级优先级自适应，支持 Skill 评估与能力合入。

## 当前版本

**v2.0.11** — 变更历史见 [CHANGELOG.md](./CHANGELOG.md)。

## 为什么需要这个工具箱？

如果你遇到过这些问题，这个工具箱就是为你设计的：

- **Playwright 直接被风控拦下**：访问小红书 / 抖音 / B站 / 微博 / GPT 时被识别为自动化，弹验证码或直接拒绝
- **登录态丢失**：每次跑脚本都要重新扫码登录，cookie 不持久
- **SPA 无限滚动抓不全**：动态加载的内容拿不到完整列表
- **多平台维护成本高**：每个站点都要单独写 selector 适配逻辑，selector 一变就崩
- **AI 平台特殊问题**：豆包思维链检测、GPT 的 ProseMirror 输入框写不进字、Gemini 图片上传走不通
- **现有 skill 能力不足**：想给已有的浏览器自动化 skill 补齐能力，但不知道差在哪

## 爬虫方案：四级降级

默认优先级自动降级，支持平台级覆盖。每个引擎默认重试 2 轮，仍失败再切换下一个。

| 级别 | 引擎 | 核心优势 | 最适合 |
|:---:|------|---------|--------|
| **1** | **CloakBrowser** | 反指纹最强 / 持久化登录态 / 真实浏览器体验 / **纯本地运行无需注册** | 有反爬的外部平台（小红书/抖音/B站）、需要维持登录态 |
| **2** | **browser-act** | **云端浏览器池 + 本地 CLI 双模**（云端需官网注册）/ 会话隔离 / 结构化截图 / 代理轮换 / AI Agent 原生设计 | Cloak 失败后的主力兜底、人机协作/代理场景 |
| **3** | **Kimi WebBridge** | 浏览器插件桥接，绕过部分前端反爬 | 前 2 级都卡住时，借助 Kimi 浏览器能力突破 |
| **4** | **Playwright** | 纯确定性执行，零依赖门槛最低 | 本地应用 / 内部系统 / 不敏感页面 |

### 平台优先级覆盖

某些平台在特定引擎上实战成功率更高，自动调整优先级：

| 平台 | 覆盖后优先级 | 原因 |
|------|------------|------|
| **小红书** | **browser-act > cloak > kimi > playwright** | browser-act 云端浏览器池绕过小红书反爬成功率更高 |
| **Gemini / 豆包 / GPT** | **cloak > playwright > browser-act > kimi** | AI 平台必须登录 + 严格风控，cloak 反指纹+持久化 profile 是唯一稳定方案。**不要用 browser-act 云浏览器池**（会丢本地登录 cookie），详见 `references/ai-platform-automation.md` |
| B站 / 抖音 / 微博 | cloak > browser-act > kimi > playwright | 默认顺序效果好，cloak 登录态持久化是关键 |

**用户偏好优先**：用户可显式指定偏好（如「以后优先用 browser-act」），覆盖默认和平台规则。也可用 `--engine-order` 强制指定。

### 兜底策略

前 2 级为最优解。遇困难点时依次尝试后 2 级看能否走通。每引擎默认重试 2 轮。

## 普通自动化方案：互补工具

当任务需要**复用用户已登录的真实浏览器**，且**不需要反检测**时，优先用 [BrowserSkill](https://github.com/Tencent/BrowserSkill)（腾讯/MIT 开源，独立工具，非引擎）。

| 维度 | BrowserSkill | 本工具箱 |
|------|-------------|---------|
| 定位 | Agent ↔ 真实浏览器桥接 | 多引擎降级 + 平台抓取经验 |
| 登录态 | **复用用户真实登录态** | 独立 profile，需重新登录 |
| 反检测 | ❌ 无 | ✅ cloak Chromium-layer patching |
| 适用 | 个人微信、内部系统、付费订阅等非反爬场景 | 公开数据爬取、反爬平台 |

**决策捷径**：任务 reads "操作用户已登录的 XX 系统" 且非反爬 → 推荐 BrowserSkill；否则用本工具箱。详见 `references/browser-skill-cross-reference.md`。

## 使用场景

### 1）存量爬虫 Skill 评估与能力合入

话术示例：
- "用 Toolbox 评估我的 XXX skill"
- "让 XXX skill 参考 Toolbox"
- "把 toolbox 能力合入 XXX"

Toolbox 会从 10 个维度（引擎覆盖/失败分类/依赖策略/平台工程等）深度分析目标 skill，输出差距报告，用户确认后自动合入对应能力。

### 2）新自动化任务

话术示例：
- "帮我获取 XXX 网站的 XXX 内容"

Agent 自动按优先级逐引擎尝试，遇到反爬/登录/验证码时按平台规则降级。

## 安装

通过 SkillHub CLI 安装（需先登录 SkillHub）：

```bash
skills_store_cli.py install browser-automation-toolbox
```

或访问 SkillHub 详情页：https://www.skillhub.cn/skills/browser-automation-toolbox

安装后重启 agent session 让 skill 加载。

## 更新

```bash
# 只检查是否有新版本
skills_store_cli.py upgrade browser-automation-toolbox --check-only

# 执行更新
skills_store_cli.py upgrade browser-automation-toolbox
```

SkillHub CLI 会自动从平台拉取最新版本覆盖本地，不需要 personal access token，也不依赖任何内部 git 仓库。

## 可视化介绍

一页图概览（4 级降级 + 平台覆盖 + 使用场景 + BrowserSkill 互补）见 `references/browser-automation-toolbox-guide.html`，可在浏览器打开。

## 参考文档索引

| 文档 | 用途 |
|------|------|
| `references/ai-platform-automation.md` | AI 平台（Gemini/豆包/GPT）自动化经验：DOM 字段、风控规避、图片上传、ProseMirror、思维链检测 |
| `references/platform-scraping-patterns.md` | 公开内容站点（小红书/B站/抖音/微博）抓取经验 |
| `references/browser-skill-cross-reference.md` | BrowserSkill 互补工具决策表与安装指引 |
| `references/skill-evaluation-guide.md` | 评估其他浏览器自动化 skill 的 5 步流程 + 10 维检查清单 |
| `references/integration-guide.md` | 把 toolbox 嵌入其他 skill/项目的 3 种模式 |
| `references/engine-contract.md` | 4 引擎抽象契约，新增引擎必读 |
| `references/browser-act.md` | browser-act 引擎适配细节 |
| `references/kimi-webbridge.md` | Kimi WebBridge 配置引导 |
| `references/dependencies.md` | 可选依赖清单与延迟安装策略 |

## License

MIT。源自实战浏览器自动化经验沉淀。
