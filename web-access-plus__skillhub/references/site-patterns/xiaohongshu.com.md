---
domain: xiaohongshu.com
aliases: [小红书, XHS]
updated: 2026-04-15
---
## 平台特征
- 搜索结果页面可直接抓取笔记卡片信息（标题、作者、点赞数）
- 搜索URL模式：`https://www.xiaohongshu.com/search_result?keyword=KEYWORD&source=web_search_result_notes`
- 笔记详情页（`/explore/NOTE_ID`）存在强反爬机制，CDP访问频繁触发"当前笔记暂时无法浏览"（error_code: 300031）
- "大家都在搜"和相关搜索词可通过页面文本提取
- 搜索结果无需登录即可展示，但详情页需要登录+验证

## 有效模式
- 搜索结果页面的 `section.note-item` 选择器可提取笔记卡片
- 卡片内 `.title` / `[class*="desc"]` 获取标题，`.author` / `[class*="name"]` 获取作者，`.like-wrapper .count` 获取点赞数
- 通过多关键词并行搜索（不同tab）提升覆盖面
- 具体歌曲内容建议通过酷狗/网易云等音乐平台榜单获取，小红书适合获取趋势和话题热度

## 已知陷阱
- 笔记详情页无法通过CDP直接访问（2026-04-15发现），会跳转到404页并显示error_code: 300031
- 点赞数超过1万会显示为"1.5万"等中文格式，需要解析
- 搜索结果中的"筛选"标签和"大家都在搜"标签没有固定CSS类名，需通过页面文本提取
