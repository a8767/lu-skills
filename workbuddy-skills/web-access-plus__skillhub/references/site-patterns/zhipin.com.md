---
domain: zhipin.com
aliases: [BOSS直聘, BOSS]
updated: 2026-06-29
---
## 平台特征
- 聊天页面URL: `https://www.zhipin.com/web/chat/index`
- **推荐牛人页面URL: `https://www.zhipin.com/web/chat/recommend`**（左侧菜单"推荐牛人"链接，`ka="menu-geek-recommend"`）
- **推荐牛人内容在 iframe 中**: `iframe[src*="recommend"]`，src 为 `/web/frame/recommend/?jobid=...&status=...&filterParams=...`
- **iframe 内容可通过 `contentDocument` 读取**（与简历 iframe 不同，推荐列表 iframe 可跨域访问）
- **候选人卡片选择器**: `.card-item` 或 `.candidate-card-wrap`
- **姓名选择器**（推荐页）: `.name`（在 `.name-wrap .row` 内）
- **期望薪资/基本信息**: `.expect-wrap`, `.row.name-wrap`
- **优势描述**: `.geek-desc` 或 `.row.row-flex.geek-desc`
- **标签**: `.tag-item`
- **工作经历时间线**: `.timeline-item`
- **打招呼按钮**: 在卡片内，文本为 "打招呼"
- 候选人列表选择器: `.geek-item-wrap`
- 候选人详情选择器: `.base-info-single-top-detail`（基本信息）、`.base-info-single-main`（经历）
- 在线简历按钮: `.btn.resume-btn-online`
- 附件简历按钮: `.btn.resume-btn-file`（可能有disabled状态）
- 操作按钮: `.operate-icon-item`（求简历/换电话/换微信/约面试/不合适）
- 简历弹窗: `.boss-popup__wrapper.resume-common-dialog`
- 简历内容在iframe中: `.resume-detail iframe`，src为`/web/frame/c-resume/`
- iframe内容由于跨域/参数限制无法直接读取，需要截图方式获取

## 有效模式
- **沟通状态 tab 切换**: tab 元素 class 为 `.chat-label-item`，文本形如 `新招呼(308)`、`沟通中`、`已约面` 等。点击该元素即可切换列表（2026-07-02 验证）
- 候选人列表可通过`.geek-item-wrap`批量获取姓名、职位、消息预览
- **候选人姓名选择器**: `.geek-name`（注意不是 `.name-box .name`）
- **职位选择器**: `.source-job`
- **消息预览**: 无固定选择器，需从 `.uid` 的 textContent 中截取（格式为 "时间 姓名 职位 消息内容"）
- `.badge-count` 在全页面有10处（含菜单59、意向标签、充值提示、通知7、记录中心1），候选人未读 badge 需限定在 `.geek-item-wrap .badge-count` 内
- 点击候选人后右侧显示详情面板，包含年龄/学历/经验/工作经历/期望
- 批量点击+提取可使用async/await配合setTimeout(600-800ms)等待
- "求简历"按钮在"新招呼"状态下disabled，需先回复消息（消耗回聊次数）才能解锁
- 已沟通过的候选人（如黄鑫科、陈启鑫）"求简历"按钮直接available
- 快速回复选项出现在消息区域底部，选择器不固定，需遍历查找

## 已知陷阱
- iframe简历内容无法通过contentDocument读取（跨域限制或缺少参数）
- contentEditable输入框设置innerText后需触发input/change事件，但BOSS直聘可能不识别
- "求简历"确认弹窗中的"确定"按钮遍历查找可能不稳定，需要检查offsetHeight>0
- 首次回聊新招呼候选人需消耗回聊次数，Agent操作可能受限
- 批量操作40个候选人时，列表可能因新消息而重新排序，index不稳定
- 候选人列表项中职位信息选择器为 `.source-job`，消息预览无固定选择器，需从 `.uid` 的 textContent 截取（去除时间+姓名+职位后即为消息内容）
- 未读数 badge 选择器: `.badge-count`（注意全局有多个，候选人未读需用 `.geek-item-wrap .badge-count` 限定）
- **CDP Proxy 调用注意**: curl POST 请求需加 `--noproxy localhost` 绕过 http_proxy 环境变量，否则返回 Exit Code 52（空响应）
