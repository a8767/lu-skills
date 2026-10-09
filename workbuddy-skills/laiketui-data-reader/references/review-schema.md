# 多维度复盘统一数据模型（review-schema）

> 本文定义 `laiketui-data-reader` 的**跨时间维度复盘数据模型**：一套指标、四类数据、四种周期，支持灵活查询与向上聚合。
> 配套引擎见 `scripts/aggregate.py`；字段来源与选择器见 `modules.md`；提取技巧见 `extraction.md`。

## 1. 总览：四周期 × 四类数据

```
                ┌─────────────── 统计数据 stats ───────────────┐
                │  本周期核心经营指标（金额/券数/流量/人群/评价） │
                └───────────────────────────────────────────────┘
  周复盘  ──────┤
  月复盘  ──────┼──► 对比数据 comparison ── 环比(qoq) / 同比(yoy)
  季复盘  ──────┤
  年复盘  ──────┤──► 趋势分析 trend ──────── 连续 N 个子周期的同一指标序列
                └──► 目标完成度 goal ──────── 实际 vs 配置目标 → 完成率%
```

任意一种复盘（周/月/季/年）都必须包含上述**四类数据**，缺任何一类都视为不完整。

## 2. 周期定义与日期计算规则

| 周期 | key 形式 | 默认范围（未指定 ref 时） | `--completed` 语义 |
|------|----------|---------------------------|--------------------|
| 周 `week` | `week/YYYY-MM-DD`（周一） | 含 ref 的自然周（周一~周日） | 上一**完整**自然周 |
| 月 `month` | `month/YYYY-MM` | 含 ref 的自然月 | 上一**完整**自然月 |
| 季 `quarter` | `quarter/YYYY-Qn` | 含 ref 的自然季 | 上一**完整**自然季 |
| 年 `year` | `year/YYYY` | 含 ref 的自然年 | 上一**完整**自然年 |

- 自然周 = 周一至周日（ISO 周）。
- 季度：Q1=1~3月，Q2=4~6月，Q3=7~9月，Q4=10~12月。
- 计算由 `aggregate.py period` 统一完成，避免人工算错边界。

## 3. 四类数据定义

### 3.1 统计数据（stats）
本周期从生意经抓取的全部核心指标（见第 6 节指标全集）。是其余三类数据的计算基础。

### 3.2 对比数据（comparison）
| 子类 | 含义 | 计算口径 |
|------|------|----------|
| 环比 `qoq` | 与**上一相邻周期**比 | (本期 − 上期) / 上期 × 100% |
| 同比 `yoy` | 与**去年同周期**比 | (本期 − 去年同周期) / 去年同周期 × 100% |

- 例：月复盘 2026-06 的环比 = vs 2026-05；同比 = vs 2025-06。
- 周复盘同比 = vs 去年同周；季/年同理。
- 缺失上一周期数据时，delta 标记 `null`（不臆造）。

### 3.3 趋势分析（trend）
按**本周期粒度**取最近 N 个连续子周期，输出同一指标的序列，用于看走势。

| 复盘类型 | 趋势粒度 | 默认 N |
|----------|----------|--------|
| 周复盘 | 周 | 8 周 |
| 月复盘 | 月 | 12 个月 |
| 季复盘 | 季 | 8 季 |
| 年复盘 | 年 | 5 年 |

- 序列最末点 = 当前复盘周期本身。
- 每个子周期需有对应 `records/<key>.json`；缺失点标记 `null`。

### 3.4 目标完成度（goal）
实际值 vs **配置目标值** → 完成率。

```
完成率% = 实际值 / 目标值 × 100%
```

- 目标值来自 `config/targets.json`（按 `客户 → 周期类型 → 指标` 配置），由运营/商家自行维护。
- 未配置目标的指标，完成率标记 `null` 并提示"未设目标"。
- 支持"年度目标自动按周期拆分"的约定：若某周期缺目标但有年目标，可用 `aggregate.py review --split-year-goal` 按历史占比或平均拆分（可选）。

## 4. 统一数据记录 Schema（canonical JSON）

每次对一个「客户 + 周期」抓数后，存为一条记录：

```json
{
  "client": "青石峡漂流",
  "period_type": "week",
  "period_label": "2026-W28",
  "period_start": "2026-07-06",
  "period_end": "2026-07-12",
  "collected_at": "2026-07-14T15:00:00",
  "source": "life-data.cn",
  "stats": {
    "gmv": 109997.80,
    "verified_amount": 55778.60,
    "refund_amount": 4213.50,
    "coupon_sold": 881,
    "coupon_verified": 379,
    "exposure": 768031,
    "store_visits": 43963,
    "live_gmv": 33160.90,
    "live_verified": 7782.60,
    "live_refund": 9070.80,
    "live_hours": 590,
    "live_sessions": 90,
    "live_exposure_users": 106770,
    "video_gmv": 26900.10,
    "video_views": 392567,
    "video_plant_value": 8353.52,
    "video_coupon": 293,
    "search_gmv": 34202.00,
    "search_verified": 14759.61,
    "search_exposure_users": 141434,
    "search_orders": 164,
    "new_customers": 261,
    "returning_customers": 112,
    "repurchase_users": 178,
    "repurchase_rate": 42.0,
    "good_reviews": 33,
    "bad_reviews": 7
  }
}
```

> `stats` 中的键即第 6 节指标全集的英文键。率类指标（`verify_rate`/`refund_rate`/`repurchase_rate`）可由 `aggregate.py` 在聚合时由分子/分母推导，也可直接存平台报告值。

## 5. 存储布局与聚合规则

### 5.1 存储布局
```
data/<客户名>/
  records/
    week__2026-07-06.json
    week__2026-07-13.json
    month__2026-07.json
    quarter__2026-Q2.json
    year__2026.json
  reviews/
    week__2026-07-06.md
    month__2026-07.md
    ...
```
> 文件名的 `/` 用 `__` 替代，规避路径分隔符。

### 5.2 聚合（roll-up）规则
为支持"灵活查询与聚合展示"，细周期可向上汇总为粗周期：

```
周 ──► 月 ──► 季 ──► 年
   └──────► 季
   └────────────► 年
      月 ────────► 年
      季 ────────► 年
```

- **可加总指标（agg=sum）**：直接求和（GMV、核销、曝光、券数、直播时长/场次、好评差评等）。
- **率类指标（agg=derive）**：用汇总后的分子/分母重新计算
  - `verify_rate = coupon_verified / coupon_sold`
  - `refund_rate = refund_amount / gmv`
  - `repurchase_rate = repurchase_users / (new_customers + returning_customers)`
- 聚合由 `aggregate.py rollup` 生成粗周期记录，后续 `review` 可直接复用。

### 5.3 灵活查询接口
`aggregate.py query` 支持按 `客户 / 周期类型 / 起止日期` 过滤已存记录，输出 JSON 或 CSV，便于跨客户、跨周期对账与看板展示。

## 6. 指标全集（METRIC_DEFS）

| 英文键 | 中文标签 | 单位 | 聚合口径 |
|--------|----------|------|----------|
| `gmv` | 成交GMV | 元 | sum |
| `verified_amount` | 核销金额 | 元 | sum |
| `refund_amount` | 退款金额 | 元 | sum |
| `coupon_sold` | 成交券数 | 张 | sum |
| `coupon_verified` | 核销券数 | 张 | sum |
| `exposure` | 线上曝光次数 | 次 | sum |
| `store_visits` | 门店页访问人数 | 人 | sum |
| `live_gmv` | 直播成交金额 | 元 | sum |
| `live_verified` | 直播核销金额 | 元 | sum |
| `live_refund` | 直播退款金额 | 元 | sum |
| `live_hours` | 直播时长 | 小时 | sum |
| `live_sessions` | 直播场次数 | 场 | sum |
| `live_exposure_users` | 直播间曝光人数 | 人 | sum |
| `video_gmv` | 视频成交金额 | 元 | sum |
| `video_views` | 视频播放量 | 次 | sum |
| `video_plant_value` | 种草价值 | 元 | sum |
| `video_coupon` | 视频成交券数 | 张 | sum |
| `search_gmv` | 搜索成交金额 | 元 | sum |
| `search_verified` | 搜索核销金额 | 元 | sum |
| `search_exposure_users` | 搜索曝光人数 | 人 | sum |
| `search_orders` | 搜索成交人数 | 人 | sum |
| `new_customers` | 新客成交数 | 人 | sum |
| `returning_customers` | 老客成交数 | 人 | sum |
| `repurchase_users` | 复购人数 | 人 | sum |
| `verify_rate` | 核销率 | % | derive（核销券数/成交券数） |
| `refund_rate` | 退款率 | % | derive（退款金额/成交GMV） |
| `repurchase_rate` | 复购率 | % | derive（复购人数/(新客+老客)） |

## 7. 复盘报告输出结构（markdown）

`aggregate.py review` 生成的 `.md` 含五个章节，对应四类数据 + 概览：

```
# <客户> <周期类型>复盘（<起>~<止>）
## 一、概览
## 二、统计数据（本周期核心指标）
## 三、对比数据（环比 / 同比）
## 四、趋势分析（最近 N 个子周期走势）
## 五、目标完成度（实际 vs 目标）
```
