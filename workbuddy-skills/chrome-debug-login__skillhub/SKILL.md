---
name: 免登录神器
description: 一次登录终身免登录。
category: devops
---

# Chrome 免登录调试浏览器

## 这是什么

让 AI Agent 操控国内平台时绕过反爬、验证码、扫码登录的方案。

**核心思路：** 创建独立 Chrome 用户数据目录 → 人类手动登录一次 → Cookie 写入磁盘 → Agent 通过 CDP 操控 → **永久免登录**。

**扩展性：** 登录了多少个平台，Agent 就能免登录操控多少个平台。每多一个平台，只需在调试浏览器中手动登录一次。

## 完整流程

### 阶段一：环境搭建（一次配置永久使用）

```
1. 创建独立用户数据目录
2. 启动Chrome调试模式（含快捷方式）
3. 验证调试端口连通
```

### 阶段二：人工登录（仅一次）

```
4. 在调试浏览器中打开目标平台
5. 手动输入账号密码完成登录
6. 关闭Chrome并重启 → 验证登录态持久化
7. 重复4-6直到所有目标平台登录完毕
```

### 阶段三：Agent使用（自动化）

```
8. Agent通过CDP获取标签页列表
9. 执行JavaScript/模拟操作完成任务
10. Cookie永不过期，无需再次登录
```

### 阶段四：扩展平台

```
11. 手动登录新平台 → Agent自动获得该平台操控能力
12. 无需修改任何代码/配置
```

---

## Step 1: 创建独立用户数据目录

Chrome 的用户目录默认在系统盘，与日常使用的主力 Chrome 共用。**必须创建独立目录**，否则调试端口会与主力 Chrome 的配置文件冲突。

```bash
# Windows
mkdir "%LOCALAPPDATA%\Google\Chrome\调试浏览器"

# macOS
mkdir -p ~/Library/Application\ Support/Google/Chrome/调试浏览器

# Linux
mkdir -p ~/.config/google-chrome/调试浏览器
```

> **为什么必须独立？** 不独立的话，主力 Chrome 退出时调试 Chrome 也会退出；且调试端口暴露的 Cookie 可能包含敏感账号信息，隔离更安全。

---

## Step 2: 启动 Chrome 调试模式

### 方式 A：桌面快捷方式（推荐）

创建快捷方式，目标填写：

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%LOCALAPPDATA%\Google\Chrome\调试浏览器"
```

参数说明：

| 参数 | 作用 | 是否必填 |
|------|------|:-------:|
| `--remote-debugging-port=9222` | 开启调试端口，监听 9222 | ✅ |
| `--remote-allow-origins=*` | 允许外部 WebSocket 连接（Chrome 128+ 默认拒绝）| ✅ |
| `--user-data-dir="..."` | 指定独立配置目录（与主 Chrome 隔离）| ✅ |
| `--new-window "URL1" "URL2"` | 启动时自动打开目标平台（可选）| ❌ |

> **注意：** 不同系统的 Chrome 路径不同。Windows 常见路径：`%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe` 或 `C:\Program Files\Google\Chrome\Application\chrome.exe`。

### 方式 B：命令行启动

```bash
# Windows (cmd)
start "" "chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%LOCALAPPDATA%\Google\Chrome\调试浏览器"

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=~/Library/Application\ Support/Google/Chrome/调试浏览器

# Linux
google-chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=~/.config/google-chrome/调试浏览器
```

### 方式 C：批处理脚本（开机自动启动）

创建 `启动调试浏览器.bat`：

```batch
@echo off
start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%LOCALAPPDATA%\Google\Chrome\调试浏览器" --new-window "https://www.baidu.com"
```

放在 `shell:startup` 目录下可实现开机自启。

---

## Step 3: 验证调试端口

启动 Chrome 后，验证端口连通：

```bash
curl http://localhost:9222/json/version
```

成功返回示例：
```json
{
  "Browser": "Chrome/148.0.7778.179",
  "Protocol-Version": "1.3",
  "WebSocket-Debugger-Url": "ws://localhost:9222/devtools/browser/..."
}
```

如果 curl 超时或拒绝连接，请检查：
1. Chrome 是否真的启动了（任务管理器查看进程）
2. 端口 9222 是否被其他程序占用
3. 防火墙是否放行 localhost 流量

---

## Step 4: 登录平台

> **核心原则：登录了多少个平台，Agent 就能操控多少个平台。**

在调试浏览器中：
1. 打开目标平台（如 `https://www.toutiao.com`）
2. 手动输入账号密码完成登录
3. 验证登录成功（页面显示头像/用户名/通知）
4. 可弹幕打开多个平台，逐个登录

**建议：** 登录期间不要关闭 Chrome。如果关闭了，重新打开后检查登录态是否持久化——页面应自动显示已登录状态。

---

## Step 5: 验证登录态

### 方法 A：直接观察（推荐）

关闭 Chrome → 再次双击快捷方式打开 → 检查各平台是否自动登录。如果登录态丢失，说明 Step 1 的独立目录没有正确创建，或者该平台不支持 Cookie 持久化。

### 方法 B：通过 CDP 检查 Cookie

```python
import json
import subprocess
from websocket import create_connection

# 获取标签页列表
result = subprocess.run(
    ["curl", "-s", "http://localhost:9222/json"],
    capture_output=True, text=True
)
tabs = json.loads(result.stdout)

# 检查目标平台的 Cookie
for tab in tabs:
    target_platforms = ["toutiao", "douyin", "xiaohongshu", "zcool", "bilibili", "weibo"]
    if any(p in tab.get('url', '') for p in target_platforms):
        ws = create_connection(tab['webSocketDebuggerUrl'], timeout=10, origin="http://localhost:9222")
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        resp = json.loads(ws.recv())
        cookies = resp["result"]["cookies"]
        ws.close()
        
        # 检查是否有 session/token 类 Cookie
        login_keywords = ['session', 'token', 'passport', 'login', 'uid', 'auth', 'sid']
        relevant = [c for c in cookies if any(k in c['name'].lower() for k in login_keywords)]
        print(f"[{tab['title'][:20]}] Cookie数: {len(cookies)}, 登录态Cookie: {len(relevant)}")
```

---

## CDP 常用操作大全

操作调试浏览器中的任意标签页：

### 1. 查看所有打开的标签页
```bash
curl http://localhost:9222/json
```

### 2. 打开新标签页
```bash
curl -X PUT "http://localhost:9222/json/new?https://www.baidu.com"
```

### 3. 关闭标签页
```bash
curl "http://localhost:9222/json/close/<PAGE_ID>"
```

### 4. 执行 JavaScript
```python
from websocket import create_connection
import json

ws = create_connection(WS_URL, timeout=10, origin="http://localhost:9222")
ws.send(json.dumps({
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "document.title",
        "returnByValue": True
    }
}))
print(ws.recv())
ws.close()
```

### 5. 点击页面元素
```python
ws.send(json.dumps({
    "id": 2,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "document.querySelector('.post-btn').click()",
        "returnByValue": True
    }
}))
```

### 6. 填写表单
```python
ws.send(json.dumps({
    "id": 3,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "document.querySelector('textarea').value = '要输入的内容'",
        "returnByValue": True
    }
}))
```

### 7. 读取页面内容
```python
ws.send(json.dumps({
    "id": 4,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "document.querySelector('.article-title').innerText",
        "returnByValue": True
    }
}))
```

---

## 扩展新平台

想增加一个平台，只需两步：

1. **在调试浏览器中点击书签或输入 URL**
2. **手动登录一次**

之后 Agent 重启后即可直接操控该平台。不需要改任何代码、不需要加任何配置。

---

## 与其他方案的对比

| 维度 | 本方案 | agent-browser | API直调 | Selenium |
|------|:------:|:-------------:|:-------:|:--------:|
| 登录态持久化 | ✅ 永久磁盘化 | ❌ 每次重登 | ⚠️ 依赖 Token 有效期 | ❌ 重复扫码 |
| 反爬能力 | ✅ 真实 Chrome 指纹 | ⚠️ 易检测 | ❌ 加密参数难破解 | ⚠️ 易检测 |
| 配置成本 | 高（首次需手动登录） | 低（pip install） | 高（逆向加密） | 中（配置 Driver）|
| 长期维护 | 无需维护 | 可能被风控 | 需跟版本更新 | 需更新 Driver |
| 多平台扩展 | ✅ 登录即用 | ❌ 每个平台单独适配 | ❌ 每个平台单独适配 | ❌ 每个平台单独适配 |

---

## 常见问题 FAQ

### Q1: Chrome 重启后 Cookie 会丢吗？
不会。独立数据目录里的 Cookie 存在 SQLite 数据库中（`Default/Cookies`），Chrome 重启后自动加载。除非手动清除浏览器数据，否则永久有效。

### Q2: CDP WebSocket 连接被拒绝（403）？
缺少 `--remote-allow-origins=*`。Chrome 128+ 默认拒绝外部 WebSocket 连接。确保启动参数包含此 flag。

### Q3: 多个 Agent 能同时连接同一个调试端口吗？
可以。CDP 支持多客户端同时连接到同一 Chrome 实例。

### Q4: Chrome 版本升级会影响吗？
一般无影响。独立数据目录会自动兼容新版 Chrome。如果遇到 Cookie 加密格式变更（极罕见），重新登录一次即可。

### Q5: 独立目录和主 Chrome 会冲突吗？
完全隔离。独立目录有自己的 Cookie、扩展、历史记录，不影响主力 Chrome。

### Q6: 换成另一台电脑还能用吗？
**不能。** Cookie 存储在本地磁盘，与绑定的机器无关，但需要在新电脑重新搭建并登录。可以把独立数据目录复制到新电脑使用，但不保证每个平台的 Cookie 都被新环境接受。

### Q7: 登录态会过期吗？
大部分平台的 Cookie 有有效期（几个月到一年不等）。过期后 Agent 会检测到登录态失效，此时在调试浏览器中刷新页面重新登录一次即可。

### Q8: 可以在 headless 模式下运行吗？
不推荐。Headless Chrome 更容易被平台检测为机器人。本方案使用真实 Chrome 窗口。

---

## 安全注意事项

1. **调试端口仅绑定 localhost（默认）** — 外部设备无法连接
2. **独立数据目录隔离** — 与主 Chrome 完全隔离
3. **建议使用小号** — 避免在调试浏览器中操作主力账号
4. **端口安全** — 任何能访问 `localhost:9222` 的进程都能控制浏览器

---

## 实例参考：双色映画工作室 @小蓝

以下为工作室实例，供参考：

| 项 | 值 |
|------|------|
| Chrome 路径 | `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe` |
| 数据目录名 | `小蓝调试` |
| 调试端口 | 9222 |
| 快捷方式 | `xiaolanLLQ.lnk`（桌面） |
| 已登录平台 | 抖音精选、今日头条、小红书、站酷 |

> **提示：** 其他人搭建时，数据目录名、端口号、快捷方式名称均可自定义。已登录平台取决于手动登录了多少个。
