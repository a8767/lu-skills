---
domain: taobao.com
aliases: [淘宝, taobao, s.taobao.com, item.taobao.com]
updated: 2026-05-12
---
## 平台特征
- 搜索页 URL 格式：`https://s.taobao.com/search?q=关键词`
- 商品卡片是 `<a>` 标签，class 含 `doubleCardWrapperAdapt`（后缀为随机 hash）
- 每个卡片包含完整商品信息：名称、价格、销量、店铺名
- 部分商品链接为 `item.taobao.com`，部分为 `detail.tmall.com`
- 页面需要登录态才能看到完整数据，CDP 直连用户 Chrome 天然携带登录态

## 有效模式
- 商品卡片选择器：`a[class*="doubleCardWrapper"]`
- 商品 ID 从 href 提取：`/[?&]id=(\d+)/`
- 价格匹配：卡片内文本 `/¥([\d.]+)/g`，取第一个匹配
- 销量匹配：卡片内文本 `/([\d.]+万?\+?人付款)/`
- 店铺名：`[class*="ShopName"]` 或文本中 `旗舰店/专卖店` 关键词匹配
- 导航新搜索：`/navigate?target=ID&url=https://s.taobao.com/search?q=新关键词`

## 已知陷阱
- 价格和销量数据可能被合并提取（如价格 48300 实际是提取错误，价格和销量数字粘连）
- 部分商品名称只是榜单名称（如"碳钢露营桌子回购榜·第9名"），缺少实际产品描述
- zsh 中 curl POST 含方括号/特殊字符会被 shell 解析，需用文件方式传 JS
- 价格超过 500 元的条目大概率是提取错误（露营桌椅品类），应过滤
- 销量含小数且不含"万"字的条目（如"39.68人付款"）可能是数据粘连错误
