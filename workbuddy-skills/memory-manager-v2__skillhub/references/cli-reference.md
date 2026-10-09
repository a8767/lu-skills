# CLI 命令完整参考

## 基础命令

### analyze — 记忆分析
```bash
memory_manager.py analyze                  # 全量分析（默认入口）
memory_manager.py analyze --lang en        # 英文输出
```

### search — 记忆搜索
```bash
memory_manager.py search -k 关键词         # 关键词搜索
memory_manager.py search -k 关键词 --tag 标签名  # 标签过滤
memory_manager.py search -k 关键词 --folder 项目名  # 文件夹过滤
memory_manager.py search -k 关键词 --mode detailed  # 详细模式
```

### load — 智能加载
```bash
memory_manager.py load --days 7            # 加载最近7天
memory_manager.py load --mode brief        # 简要模式
memory_manager.py load --days 30 --mode normal  # 30天普通模式
memory_manager.py load --folder 项目A      # 加载指定文件夹
```

### report — 记忆报告
```bash
memory_manager.py report                   # 生成记忆文件清单
```

### rank — 重要性分级
```bash
memory_manager.py rank                     # 四维评分（mtime/size/keyword/age）
memory_manager.py rank --days 30          # 仅评估30天内文件
memory_manager.py rank --folder 项目A     # 指定文件夹
```

### summarize — 摘要生成
```bash
memory_manager.py summarize                # 生成所有记忆摘要
```

## Token 管理

### token-check — Token检查
```bash
memory_manager.py token-check              # 今日Token消费 vs 预算
memory_manager.py token-check --budget 5000  # 自定义每日预算
```

输出字段：
- `used_tokens`: 今日估算消耗
- `budget`: 每日预算
- `warning_level`: 🟢green/🟡yellow/🔴red
- `note`: "基于字符数估算，非实际API消耗"

### token-trends — Token趋势
```bash
memory_manager.py token-trends             # 按周统计（默认）
memory_manager.py token-trends --period month  # 按月统计
memory_manager.py token-trends --period daily --days 14  # 近14天逐日
```

输出包含：
- `daily`: 逐日数据 `[{date, tokens, operations_count}]`
- `aggregated`: 聚合数据 `[{label, tokens, operations_count}]`
- `totals`: `{days_with_data, total_tokens, total_operations, avg_daily_tokens}`

CLI 输出包含可视柱状图（█ 字符）。

## 缓存与清理

### cache-reminder — 缓存提醒
```bash
memory_manager.py cache-reminder           # 含Token预警+缓存状态
```

### cache-clean — 缓存清理
```bash
memory_manager.py cache-clean              # 预览模式
memory_manager.py cache-clean --execute    # 执行清理（含前后大小对比）
```

返回字段：`before_kb` / `after_kb` / `delta_kb`（清理前后对比）

### auto-clean — 差异化自动清理
```bash
memory_manager.py auto-clean               # 预览模式
memory_manager.py auto-clean --execute     # 执行清理
```

按内容类型差异化处理：
- 推送类：超保留期可清理
- 个人/工作类：超提醒间隔才提醒
- 其他类：超保留期建议清理

### dedup — 去重
```bash
memory_manager.py dedup                    # 预览重复文件
memory_manager.py dedup --execute          # 执行去重
```

### scan — 工作空间扫描
```bash
memory_manager.py scan                     # 扫描缓存和存储状态
```

## 数据安全

### export / import — 导出导入
```bash
memory_manager.py export --output bak.zip  # 导出为ZIP
memory_manager.py import --file bak.zip    # 从ZIP导入
memory_manager.py import --file bak.zip --confirm  # 确认覆盖
memory_manager.py import --file bak.zip --mode overwrite  # 覆盖模式
```

### backup / restore — 备份恢复
```bash
memory_manager.py backup --path "D:/备份"   # 增量备份
memory_manager.py restore                   # 恢复最近备份
```

## Prompt 模板管理

### prompt-list — 列出模板
```bash
memory_manager.py prompt-list .            # 列出所有
memory_manager.py prompt-list . --tag 代码审查  # 按标签过滤
```

### prompt-get — 获取模板
```bash
memory_manager.py prompt-get 代码审查       # 获取模板内容+元数据
```

### prompt-save — 保存模板
```bash
memory_manager.py prompt-save 代码审查 . --content "请审查以下代码..." --tags "代码审查,重构"
memory_manager.py prompt-save 代码审查 . --content "..." --description "代码审查模板" --category "开发"
```

保存为 `PROMPT_代码审查.md`，自动版本递增。

### prompt-search — 搜索模板
```bash
memory_manager.py prompt-search . --keyword 审查   # 关键词搜索
memory_manager.py prompt-search . --tag 代码审查    # 标签搜索
```

## 其他

### doctor — 诊断
```bash
memory_manager.py doctor                   # 健康检查+安全评分
```

检查项：模块完整性、符号链接、配置值域、异常大文件、i18n同步。

### config — 配置
```bash
memory_manager.py config --key lang --value en  # 切换英文
memory_manager.py config --key budget --value 5000  # 设置预算
```

### 语言切换
```bash
memory_manager.py --lang zh analyze        # 中文
memory_manager.py --lang en analyze        # English
```

## 意图识别决策树

```
输入包含"记忆"或"memory"?
├── 是 → 包含动作词?
│   ├── 查看/列表/清单/报告 → report 或 analyze
│   ├── 搜索/查找 + 关键词 → search -k [关键词]
│   ├── 加载/读取 → load (--days 自动推断)
│   ├── 清理/删除/归档 → auto-clean / cache-clean / dedup (需确认)
│   ├── 摘要/总结 → summarize
│   ├── 备份/导出 → export; 恢复/导入 → import
│   ├── 分析/状态/诊断 → analyze / doctor
│   └── 分级/排名/排序 → rank
├── 否 → 包含 Token/token?
│   ├── 统计/检查/预警/预算 → token-check
│   ├── 趋势/统计图表/周月 → token-trends
│   └── 省/节省/优化 + Token → summarize + token-check 组合
├── 否 → 包含 缓存/cache?
│   ├── 提醒 → cache-reminder (含内置 Token 预警)
│   └── 清理 → cache-clean (默认预览模式)
└── 否 → "记忆管家"(品牌词) → analyze (默认全量分析)
```

## 输出格式

### 成功响应
```json
{
  "status": "success",
  "command": "命令名",
  "summary": "一句话结果",
  "details": {},
  "suggestions": [],
  "next_actions": []
}
```

### 错误响应
```json
{
  "status": "error",
  "command": "命令名",
  "error_type": "错误分类",
  "message": "用户可读说明",
  "recovery": []
}
```

### Token 敏感操作
```json
{
  "token_usage": {
    "estimated_tokens": 1234,
    "budget_used_pct": 45,
    "warning_level": "green"
  }
}
```
