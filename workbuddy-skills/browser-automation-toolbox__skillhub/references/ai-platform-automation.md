# AI 平台自动化经验（Gemini / 豆包 / GPT）

本文件记录三大 AI 平台的自动化操作经验。与 `platform-scraping-patterns.md`（抓取公开内容站点）互补：AI 平台涉及登录态、风控、SPA、ProseMirror、思维链流式生成等特殊问题，需要专门的 DOM 字段和策略。

> 所有 DOM 字段均经 dump 实证，避免启发式猜测。

## 1. 为什么 AI 平台需要专门章节

| 维度 | 公开抓取站点（小红书/B站等） | AI 平台（Gemini/豆包/GPT） |
|---|---|---|
| 登录态 | 多数可匿名抓取 | **必须登录**，cookie 失效即失败 |
| 风控 | 抓取频率限制 | **真人校验**（验证码），重启 Chromium 即触发 |
| 内容形态 | 静态卡片/列表 | **流式生成**，思维链+正文分离 |
| 输入框 | 普通 textarea | **ProseMirror contenteditable**（React 受控） |
| 图片上传 | 不涉及 | **drop event / 专用 file input**， setInputFiles 常失效 |
| 输出格式 | 文本+链接 | **markdown 还原**，innerText 丢失格式 |

## 2. 引擎优先级（AI 平台特殊覆盖）

| 平台 | 推荐引擎优先级 | 原因 |
|---|---|---|
| Gemini AI Studio | **cloak > playwright > browser-act > kimi** | Gemini 检测 CDP attach，必须用 cloak 反指纹 |
| 豆包 | **cloak > playwright > browser-act > kimi** | 豆包风控严格，全量 DOM 扫描必触发验证码 |
| GPT (chatgpt.com) | **cloak > playwright > browser-act > kimi** | GPT 检测自动化特征，cloak 持久化 profile 保登录 |

**不要用 browser-act 云浏览器池**跑 AI 平台——会丢失本地登录 cookie。AI 平台必须用本地 cloak + 持久化 profile。

## 3. 风控规避铁律（AI 平台专用）

1. **evaluate 里绝不能 `querySelectorAll('div, span')` 全量遍历**——风控必检异常 DOM 扫描。需要找元素时用语义化 selector（`[role="..."]`、`[data-testid="..."]`、`button:has-text(...)`）。
2. **按钮点击优先 Playwright 原生 `locator.click()`**（走 humanize 拟人路径），而非 `evaluate + dispatchEvent(MouseEvent)` 坐标点击。后者是自动化特征。
3. **只在目标平台 page 上操作，不波及其他 tab**。多 tab 共享 context，但操作要严格限定在当前平台的 page。
4. **非必要不重启 Chromium**：重启 = 指纹变化 = 风控真人校验。只有冷启动（Chromium 没开）和 CONTEXT 失效（Chromium 被整体关闭）时才启动/重启。改 provider 代码后，等用户确认时机或下次自然需要时再重启。
5. **profile 持久化**：每个平台用独立 profile（如 `~/.cloakbrowser-ai-platform-profile`），cookie 保留。冷启动后无需重新登录。

## 4. 三平台真实 DOM 字段速查

### 4.1 豆包专家模式思维链/正文

```html
<div class="group/thinking-box-root" data-thinking-box-expanded="true|false">
  <div data-thinking-box="content">
    <div data-thinking-box="title">[step 标题或"已完成思考"]</div>
    <div data-thinking-box="step-message">[思维链文本]</div>
  </div>
</div>
<div data-streaming="true|false" class="md-box-root">[正文]</div>
```

| 状态字段 | 值 | 含义 |
|---|---|---|
| `data-thinking-box-expanded` | `"true"` | 思维链生成中 |
| `data-thinking-box-expanded` | `"false"` | 思维链已折叠完成 |
| `.dot-flashing-mIsXoz` / `.dot-BU8RO9` | visible | 思考指示器在闪 |
| `div.md-box-root[data-streaming]` | 不存在 | 正文还没开始 |
| `div.md-box-root[data-streaming]` | `"true"` | 正文流式生成中 |
| `div.md-box-root[data-streaming]` | `"false"` | 正文已生成完 |

⚠️ **"已完成思考"文本只在思维链折叠后出现，不能用作生成期检测**。

### 4.2 GPT 图片上传

**三个 file input**（不止一个）：

| input id | data-testid | accept | 用途 |
|---|---|---|---|
| `upload-files` | （无） | （无） | 通用文件上传 |
| `upload-photos` | `upload-photos-input` | `image/*` | **图片专用（传图用这个）** |
| `upload-camera` | （无） | `image/*` + `capture="environment"` | 相机拍照 |

附件按钮：`[data-testid="composer-plus-btn"]` aria-label="添加文件等"

输入框：`<div contenteditable="true" id="prompt-textarea" class="ProseMirror" role="textbox">`（同 ID 有 hidden textarea fallback，Playwright `#prompt-textarea` 取第一个 hidden）

上传后预览：

```html
<div role="group" aria-label="文件名.png" class="group/file-tile ...">
  <button aria-label="打开图片：用户上传的图片" ...>
    <img src="https://chatgpt.com/backend-api/estuary/content?id=file_xxx&ts=...&sig=...">
  </button>
</div>
```

**预览 src 格式：`https://chatgpt.com/backend-api/estuary/content?id=file_xxx`**（不是 `blob:` / `data:` / `upload`！）

### 4.3 Gemini AI Studio

- 输入框：`textarea` 在 `ms-autoscroll-container` 内部
- 模型切换：subtitle 含 `3.5`（点）形式，不是 `3-5`（连字符）
- 错误检测：扫最后一个 `ms-chat-turn` 整体
- 图片预览：`.prompt-media-item-container`（每文件 1 chip）
- 滚动容器：`ms-autoscroll-container`（不是 body）
- `display: contents` wrapper 会让 `offsetParent` 判断失效；可见性判断要穿透 wrapper（`window.getComputedStyle(c).display === 'contents'` 时递归到子元素）

## 5. 图片上传策略（按平台）

### 5.1 Gemini：drop event 注入（唯一方案）

**Gemini AI Studio menu upload 触发原生 OS file picker，setInputFiles 完全走不通**。唯一稳定方案：DataTransfer drop event 直接注入 textarea。

```python
# 流程：
# 1. base64 → 临时文件
# 2. evaluate 内创建 DataTransfer + File 对象
# 3. dispatch dragenter/dragover/drop event 到 textarea
# 4. 等 3.5s 校验预览（.prompt-media-item-container 计数）
# 5. 不足逐张 drop 补传
```

### 5.2 豆包：set_input_files 直查（不做预览计数）

豆包 `input[type=file]` 默认在 DOM（hidden），`query_selector` 策略1直接找到，无需点按钮。**`set_input_files` 成功即可信，不要做预览计数**（豆包预览 selector 不稳定，强行计数会触发误补传导致图片翻倍）。有图时 Enter 不发送，需按钮点击 fallback。

### 5.3 GPT：set_input_files 到 #upload-photos（主路径）

1. **主路径**：`set_input_files` 到 `#upload-photos`（图片专用 input，已验证可用）
2. **兜底1**：drop event 注入 ProseMirror
3. **兜底2**：逐张 `set_input_files` 补传
4. 每步后校验预览（`[role="group"][aria-label] img[src*="estuary/content"]` 计数），达 expected 立即 return

```python
for sel in ['#upload-photos', 'input[data-testid="upload-photos-input"]', 'input[accept*="image"]']:
    fi = await page.query_selector(sel)
    if fi:
        await fi.set_input_files(temp_files)
        set_ok = True
        break
```

### 5.4 通用防重复三件套

1. `_upload_in_progress` 防重入标志（避免 send 被重复调用时二次上传）
2. `set_input_files` 成功后立即校验预览（用真实 DOM 字段，不假设 src 格式）
3. 按钮匹配排除"更多"/"+"（避免展开面板触发误操作）

## 6. ProseMirror 输入（GPT 专用）

GPT `#prompt-textarea` 是 ProseMirror（React contenteditable）。ClipboardEvent / `execCommand('insertText')` / React setter 全部无法写入（textLen=0）。**唯一可靠方案：Playwright 原生 `keyboard.type()`**——逐字符 dispatch keydown/keypress/input/keyup，完整经过浏览器事件管线 → ProseMirror 能正确处理 → React 状态更新 → 发送按钮出现。

humanize fast 模式下 ~25ms/字符，"Say hello"(9字) 约 300ms。

```python
await inp.click()
await sleep_ms(200)
await page.keyboard.type(prompt, delay=20)
```

## 7. markdown 还原铁律

`element.innerText` 只返回纯文本，**永远不要**用它做 markdown 还原——必须走 DOM 结构感知的还原引擎，穿透 display:contents、SUP 引用、GFM 表格、列表、代码块。

通用做法：给目标容器打临时标记，然后用 markdown 还原脚本（如 [turndown](https://github.com/mixmark-io/turndown) 或自实现的 DOM walker）按 selector 提取：

```js
// 给目标容器打临时标记
formalBox.setAttribute('data-bot-target', '1');
// 用 DOM 结构感知的还原引擎提取 markdown
const md = await page.evaluate(myMarkdownExtractor, {
    selectors: ['[data-bot-target="1"]'],
    preferScores: false,
    ignoreThinking: true,
});
formalBox.removeAttribute('data-bot-target');
```

## 8. 诊断套路（DOM dump 实证）

**永远不要靠经验猜 selector**——必须 DOM 实证。

### 8.1 用 page.evaluate 抓 outerHTML

```python
# 抓最后一个 assistant 消息容器的完整 outerHTML
data = await page.evaluate("""
() => {
    const isVisible = (el) => el && el.offsetParent !== null;
    const asstSel = '[data-role="assistant"], [class*="assistant-message"], ...';
    const msgs = Array.from(document.querySelectorAll(asstSel)).filter(isVisible);
    if (msgs.length === 0) {
        // fallback: 抓 main 区域
        const main = document.querySelector('main') || document.body;
        return { error: 'no-assistant-msg', mainOuterHTML: main.outerHTML.slice(0, 30000) };
    }
    const lastMsg = msgs[msgs.length - 1];
    return {
        msgCls: lastMsg.className,
        msgTextLen: (lastMsg.innerText || '').length,
        children: Array.from(lastMsg.children).map(c => ({
            tag: c.tagName, cls: c.className, textLen: (c.innerText||'').length,
        })),
        outerHTML: lastMsg.outerHTML.slice(0, 30000),
    };
}
""")
```

### 8.2 定时 dump 捕捉临界状态

发送 query 后按时间计划（如 [3, 6, 10, 14, 18, 21, 24, 28, 31, 35, 40, 50, 70, 100, 150] 秒）多次调 page.evaluate 抓 DOM，把每次响应保存为 JSON 文件。然后分析每个时间点的 DOM 状态字段值（`data-thinking-box-expanded`、`data-streaming`、`dot-flashing` 是否在等），定位真实状态字段。

### 8.3 反查真实 selector

dump 文件拿到后，用 Python `re.findall(r'class="([^"]+)"', html)` + 关键词过滤（`think`/`reason`/`chain`/`step`/`answer`/`formal`/`response`/`message`）找候选 class。再 `html.find('关键词')` 找上下文，确认真实 selector。

## 9. is_complete 完成检测策略（流式生成专用）

AI 平台流式生成时，typing 指示器消失**不等于完成**——豆包思维链 step 之间停顿 4s+ 会误判。检测顺序：

1. 停止按钮可见 → not-complete
2. 思维链展开状态（豆包专家模式 `[data-thinking-box-expanded="true"]`）→ not-complete
3. 思考指示器闪烁（`.dot-flashing-mIsXoz`）→ not-complete
4. 正文区不存在（`div.md-box-root[data-streaming]`）→ not-complete
5. 正文区 `data-streaming="true"` → not-complete（正文流式中）
6. `data-streaming="false"` → 走常规 no-generating-signal 完成检测

### 兜底分支必须检查 thinking 状态

如果有"内容稳定 N 秒兜底 done"逻辑，必须在兜底前检查 is_complete reason：

```python
is_expert_thinking = comp_reason and comp_reason.startswith("expert-")
if last_content and stable_count >= 5 and since_grow >= 4 and not is_expert_thinking:
    # 兜底 done
```

否则思维链 step 之间停顿 4s+ 会触发兜底，根本没等到正文。

## 10. 已验证场景

### 10.1 单图 + 简单问题（GPT）

- 100x100 纯红色 PNG + "请简短描述这张图片的内容和颜色"
- GPT 正确回答："这是一张纯红色的方形图片，整个画面均为鲜艳的红色。"

### 10.2 双图 + 区分问题（GPT）

- 100x100 红 + 100x100 蓝 + "请分别简短描述每张图片的颜色（标明图1和图2）"
- GPT 正确回答："图1：整体为鲜艳的红色。图2：整体为鲜艳的蓝色。"

### 10.3 专家模式思维链检测（豆包）

时间线（验证通过）：

```
t=21s:  正在思考 (thinking-box-expanded=true)
t=24-31s: step1/step2 思维链生成
t=40s:  已完成思考 + 正文开始 (data-streaming=true)
t=50s:  正文稳定 (data-streaming=false) → done
content 完整保留 ### 标题、**加粗**、- 列表等 markdown 结构
```

## 11. 已知限制

- Gemini AI Studio Run 按钮：图片上传后 Run 按钮延迟出现，retry 6 次仍可能 no-run（Run 按钮文本不是 "Run"/"运行"，可能是图标按钮）。Control+Enter (keyboard) 兜底发送有效但需等 8s。
- GPT `#prompt-textarea` 同 ID 多元素陷阱：同 ID 同时存在 hidden textarea fallback 和可见 ProseMirror div，Playwright `#prompt-textarea` 取第一个（hidden）。用 `[role="textbox"]` 或 `[contenteditable="true"]` 等更精确的 selector。
- GPT 单次最多 2 张图，超出截断。
- 豆包专家模式模式切换耗时 ~30s（菜单展开 + humanize 拟人点击）。

## 12. 与 toolbox 其他 reference 的关系

- `platform-scraping-patterns.md`：抓取公开内容站点（小红书/B站/抖音/微博），与本文互补
- `engine-contract.md`：4 引擎抽象契约，AI 平台用 cloak 引擎
- `integration-guide.md`：把 toolbox 嵌入其他 skill/项目的 3 种模式
- `skill-evaluation-guide.md`：评估其他浏览器自动化 skill 的 5 步流程
