# 记忆宫殿示例

## 首次使用流程

### 运行分析
```bash
python3 scripts/analyze.py
```

### 输出示例
```
=== 记忆宫殿分析 ===
扫描文件：45个
发现结构：3层（收件箱/归档/精华）

推荐结构：6层
  1F 收件箱（新内容）
  2F 项目层（检测到3个项目）
  3F 技术层（系统配置类笔记）
  4F 经验层（踩坑/学习记录）
  5F 归档层（已完成）
  6F 精华层（重要总结）

请确认结构[Y/n]? 
```

### 确认方式
- 输入 `y` 确认推荐
- 输入数字修改层数
- 输入 `n` 自定义

## 定期凝练

### 每日凝练
```bash
python3 scripts/condense.py --daily
```
- 追加今日记录到当日文件
- 整理临时文件到收件箱

### 每周凝练
```bash
python3 scripts/condense.py --weekly
```
- 从本周记录提取精华
- 更新 MEMORY.md

### 每月凝练
```bash
python3 scripts/condense.py --monthly
```
- 合并整理
- 优化目录结构

## 配置示例

### 最简配置（3层）
```json
{
    "layers": 3,
    "layerNames": ["收件箱", "归档", "精华"]
}
```

### 进阶配置（6层）
```json
{
    "layers": 6,
    "layerNames": ["收件箱", "项目", "技术", "经验", "归档", "精华"],
    "refineSchedule": {
        "daily": "23:00",
        "weekly": "sunday",
        "monthly": "last"
    }
}
```

## 目录结构

安装后会自动创建：
```
.palace/
├── config.json      # 你的配置
└── stats.json       # 统计信息

memory/
├── 2026-05-05.md    # 每日记录
├── MEMORY.md        # 精华
└── palace/
    ├── 1F-收件箱/
    ├── 2F-项目层/
    ├── 3F-技术层/
    ├── 4F-经验层/
    ├── 5F-归档层/
    └── 6F-精华层/
```
