---
domain: wx.mail.qq.com
aliases: [QQ邮箱, QQ Mail]
updated: 2026-05-12
---
## 平台特征
- URL格式: `https://wx.mail.qq.com/home/index?sid=XXX#/list/1/1`
- SPA应用，hash路由，URL不变但内容切换
- 邮件列表和详情在同一页面，点击列表项后右侧展开详情面板
- 附件下载走浏览器默认下载机制，保存到 ~/Downloads/

## 有效模式
- 邮件列表项选择器: `.mail-list-page-item`
- 邮件详情面板: `.mail-list-reader-wrap`
- 搜索框: 先点击 `.mail-lazy-search-wrap` 展开，再操作 `input.filter-input`
- 附件操作按钮区: `.attach-operate-btns`，下载按钮为 `.attach-operate-btns .xmail-ui-btn`（文本含"下载"）
- `innerText` 可获取SPA渲染后的完整文字内容
- 点击邮件列表项后详情面板在右侧展开，无需URL跳转

## 已知陷阱
- SPA框架绑定，直接设置 input.value 不触发响应，需用 nativeInputValueSetter 或改用列表扫描
- innerHTML 可能只拿到框架壳子（空div），内容通过SPA动态渲染
- 搜索URL跳转会导致 chrome-error，必须在页面内操作
- location.href 虽然包含hash但实际页面状态由SPA控制
- 邮件列表项的 `textContent` 包含完整邮件预览（发件人+主题+摘要），可用 indexOf 匹配关键词
