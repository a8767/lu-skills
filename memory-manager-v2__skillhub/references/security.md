# 安全特性详细说明

## 防御矩阵

| 检测项 | 防护次数 | 实现方式 |
|--------|:--------:|----------|
| 代码注入 (eval/exec/__import__) | 0 向量 | AST 扫描确认零使用 |
| 路径穿越 (path traversal) | 14 处 | safe_resolve + relative_to 校验 |
| 符号链接 (symlink) | 19 处 | is_symlink 全跳过 |
| ZIP Slip (解压路径逃逸) | 5 层 | 分量黑名单 + 绝对路径拒绝 + 反斜杠规范 + 空路径拒绝 + resolve 边界 |
| ZIP Bomb (压缩炸弹) | 4 层 | 单文件1MB预检 + 解压总大小50MB + 条目数1000 + 实时写入追踪 |
| 文件类型白名单 | 1 处 | 仅允许 .md 和 .summary |
| XSS (HTML注入) | 全字段 | html.escape() 转义所有用户输入 |
| 裸异常捕获 | 0 处 | AST 扫描确认无 bare except |
| 文件大小限制 | 全局 | 单文件1MB / 累计5MB |
| 删除确认 | 34 处 | Y/N 机制 + 非TTY拒绝 |

## 安全门禁详细规则

### 只读操作（直接执行）
- analyze, report, search, load, rank, token-check, token-trends
- doctor, cache-reminder, summarize, prompt-list, prompt-get, prompt-search

### 预览操作（默认 dry-run）
- auto-clean, cache-clean, dedup, scan
- 用户说"执行"或加 `--execute` 参数时真正执行
- 返回预览清单供用户确认

### 破坏性操作（必须 --confirm）
- import, restore, clean, archive
- import_memories() 额外5层 ZIP Slip 防御
- 非交互终端自动拒绝破坏性操作

### 配置修改（交互式引导）
- config 命令逐步确认
- 值域白名单校验（retention_days 1-365, lang zh/en 等）

## 内容分类保护

| 类型 | 保留期 | 清理策略 |
|------|--------|----------|
| 推送类 (push) | 可配（默认7天） | 超期建议清理 |
| 个人/工作 (personal_work) | 可配提醒间隔（默认5天） | 仅提醒，不自动删 |
| 核心记忆 (MEMORY.md) | 永久 | 永不删除 |
| 其他 (other) | 可配（默认7天） | 超期建议清理 |

## doctor 安全自检项

1. 模块完整性 — 检查所有 .py 文件是否存在
2. 符号链接 — 扫描 memory/ 目录是否有可疑链接
3. 配置值域 — 校验 config.json 中所有值是否在合法范围
4. 异常大文件 — 检查超过 1MB 的记忆文件
5. i18n 同步 — 验证 zh/en 键数一致
