# 林客商家数据读取链路规范（Data-Reading Pipeline Spec）

> **本文件由 `tools/sync_skill_pipeline.py` 自动生成自 `tools/fetch_list_panel.py`（PIPELINE_VERSION=1.0.0）。请勿手工编辑——修改链路后运行同步脚本重新生成。**

---

## 接口（API 直连，绕过日历）

| 项 | 值 |
|----|----|
| 方法 | POST |
| 路径 | `/data/life_partner/center/merchant/v3/list_panel` |
| Query | `ac_app=10159`、`accountId=<林客子账号ID>` |
| 鉴权 | `fetch(..., {credentials:'include'})` 复用页面 cookie，**无需 CSRF token** |
| Content-Type | `application/json` |
| Body | `{"data_type":"all_merchant_cnt","page":1,"limit":200,"start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD"}` |

> accountId / ac_app 来自页面真实请求。默认值对应本代运营账号，跨账号时用参数覆盖。

## 响应形状

```json
{ "code": 0, "data": [ /* 商家记录数组 */ ], "total": 84, "totalShow": 84 }
```

- `j.data` 是**数组**（不是 `{data:[...]}`）。兼容取值：
  `Array.isArray(j.data) ? j.data : (j.data && j.data.data) || []`
- `limit=200` 单页可覆盖当前 84 家；未来商家数 >200 时需翻页（本模块暂未实现，按需扩展）。

## 字段映射（原始字段 → 归一化键）

| 原始字段 | 归一化键 | 说明 |
|----------|----------|------|
| `merchant_id` | `id` | 商家 ID |
| `life_account_name` | `name` | 商家名称 |
| `industry_name` | `industry` | 行业 |
| `merchant_industry` | `category` | 类目 |
| `service_type`（数组） | `mode` | 合作模式，数组 join ',' |
| `follower_name`（数组） | `follower` | 跟进人，数组 join ',' |
| `merchant_manage_score` | `score` | 经营分（见下方补分逻辑） |
| `pay_amount` | `pay` | 支付 GMV（元） |
| `confirm_amount` | `verified` | 核销 GMV（元） |
| `refund_amount` | `refund` | 退款 GMV（元） |
| `indirect_item_pay_amount` | `video` | 视频直接支付 GMV |
| `room_pay_amount` | `live` | 直播支付 GMV |
| `ledger_commission` | `commission` | 总预估佣金 |
| `ledger_smc_commission` | `providerCommission` | 服务商预估佣金 |
| `ledger_talent_commission` | `promoCost` | 推广佣金成本（=总-服务商） |
| 衍生 | `verifyRate` | 核销率 = verified / pay |
| 衍生 | `refundRate` | 退款率 = refund / pay |

## 经营分补分（关键陷阱）

月份聚合时 `merchant_manage_score` 常返回 **-1 哨兵**（无效）。
真实经营分需以**短周期窗口**重新拉取（实测当月 17~23 日窗口可命中真实分 ~100+）。

`fetch_merchants(start, end)` 内部流程：
1. 拉全量月份 `fetch_array(start, end)`；
2. 额外拉 `fetch_array(当月17日, 当月23日)` 作为经营分窗口；
3. 按 `merchant_id` 建分数字典；
4. `transform(rec, score_override=分数窗口命中的真实分)`，优先用真实分，否则取原分（>0 才有效，否则记 0）。

> 分数窗口命中率约 16~50/月（部分商家该窗口无数据），未命中者记 0，属已知口径限制。

## 历史快照机制（前端复用）

归一化后的 `list` 写入 `data/history/{yyyy-MM}.json`：

```json
{
  "key": "month:2026-08",
  "label": "2026-08-01 ～ 2026-08-31",
  "statTime": "2026-08-01 ～ 2026-08-31",
  "count": 84,
  "list": [ /* 归一化记录 */ ],
  "savedAt": "ISO 时间戳"
}
```

并在 `data/history/list.json` 维护 `{"periods":[{key,label,file,count,statTime}...]}`。
服务端 `server.js` 暴露 `/api/history`（读 list.json）、`/api/history/data?file=`（读对应快照，防路径穿越）。
前端「门店数据管理」页「选择月份数据」下拉即消费这两条接口。

## 与 DOM 抓取（extract_daiyunying.py）的关系

- **本链路（API 直连）**：适合**历史月份补齐 / 全月聚合 / 任意 start~end 区间**，完全绕过失灵的日历翻月。
- **DOM 抓取（extract_daiyunying.py）**：适合**当前周期单页实时拉取**（读真实 DOM 表格 + 翻页），
  但历史月份翻月不可自动化，故历史场景应改用本链路。
- 两者输出字段一致（归一化键相同），可互换。

## 用法示例

```python
import fetch_list_panel as fpl
import ld  # skill 的 CDP 客户端

inst = ld.LD(target_hint="life-partner")
recs = fpl.fetch_merchants(inst, "2026-08-01", "2026-08-31")
print(len(recs), "家；首商家", recs[0]["name"], "经营分", recs[0]["score"])
snap = fpl.build_month_snapshot(recs, "2026-08", "2026-08-01", "2026-08-31")
```

命令行独立测试单月：

```bash
python fetch_list_panel.py --start 2026-08-01 --end 2026-08-31 --out out/2026-08.json
```
