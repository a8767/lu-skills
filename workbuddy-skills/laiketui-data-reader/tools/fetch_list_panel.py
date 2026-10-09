# -*- coding: utf-8 -*-
"""
fetch_list_panel.py — 林客商家数据「API 直连」取数链路（优化版 / 推荐首选）

本文件是 laiketui-data-reader skill 的**权威数据读取链路（single source of truth）**。
任何项目（personal-workbench 等）都应直接 `import fetch_list_panel as fpl` 复用本模块，
**不要在本项目内再复制一份 fetch / transform 逻辑**——这样 skill 优化链路时，所有消费方自动跟随最新版本。

## 为什么需要这条链路（实测结论，2026-08-21）
林客商家数据页（life-partner.cn → 商家数据 → 商家列表）的「自定义时间」双月日历，
其**翻月箭头 / 标题 / 年月 span 对自动化完全无响应**（真实鼠标 / JS click 均实测失效）。
因此走 UI 翻月补齐历史月份在自动化下不可行。
→ 改为**页面内 fetch 直连真实接口**，参数直接带 start_date/end_date，**彻底绕过日历**，
数据仍来自林客真实会话（页面 cookie），等价于补齐任意月份。

## 接口
POST /data/life_partner/center/merchant/v3/list_panel?ac_app=10159&accountId=1748387674768388
body: {"data_type":"all_merchant_cnt","page":1,"limit":200,"start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD"}
fetch 选项: { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:... }
  - credentials:'include' 复用页面 cookie（用户已登录的林客会话），**无需 CSRF token**。
  - accountId / ac_app 取自页面真实请求（默认值为本代运营账号，可通过参数覆盖）。

## 响应形状
{ "code":0, "data":[ ...商家记录... ], "total":84, "totalShow":84 }
  - 注意 j.data 是**数组**，不是 {data:[...]}。取数时做兼容：Array.isArray(j.data)?j.data:(j.data&&j.data.data)||[]。
  - 单页 limit=200 足够覆盖当前 84 家；若未来 >200 家需翻页（本模块默认 limit=200）。

## 字段映射（原始 → 归一化）
详见 SPEC 常量与下方 transform()。

## 经营分陷阱（重要）
月份聚合时 merchant_manage_score 常返回 **-1 哨兵**（无效）。
真实经营分需以**短周期窗口**（当月 17~23 日）重新拉取才返回正常值（~100+）。
故 fetch_merchants() 在拉全量月份后，额外用当月 17~23 日窗口补真实分，按 merchant_id 合并。

## 用法
    import fetch_list_panel as fpl
    inst = ld.LD(target_hint="life-partner")   # 复用 skill 的 ld.py
    recs = fpl.fetch_merchants(inst, "2026-08-01", "2026-08-31")
    snap = fpl.build_month_snapshot(recs, "2026-08", "2026-08-01", "2026-08-31")

命令行（独立测试单月）：
    python fetch_list_panel.py --start 2026-08-01 --end 2026-08-31 [--account-id ...] [--ac-app ...] [--out file.json]
"""
import json
import sys
import datetime
import calendar

# ---- 版本与权威规范（sync_skill_pipeline.py 会读取这两个常量重新生成 data-pipeline.md）----
PIPELINE_VERSION = "1.0.0"
SPEC = """\
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
"""

DEFAULT_ACCOUNT_ID = "1748387674768388"  # 林客子账号（来自页面真实请求）
DEFAULT_AC_APP = "10159"
DEFAULT_SCORE_WINDOW = (17, 23)  # 经营分补分窗口（当月 17~23 日）


def _safe(v, d=0):
    return v if isinstance(v, (int, float)) else d


def transform(rec, score_override=None):
    """把一条原始商家记录归一化为前端期望形状。score_override 优先（经营分窗口补到的真实分）。"""
    pay = _safe(rec.get("pay_amount"))
    verified = _safe(rec.get("confirm_amount"))
    refund = _safe(rec.get("refund_amount"))
    verify_rate = round(verified / pay, 4) if pay else None
    refund_rate = round(refund / pay, 4) if pay else None
    service = rec.get("service_type") or []
    if isinstance(service, list):
        service = ",".join(service)
    followers = rec.get("follower_name") or []
    if isinstance(followers, list):
        followers = ",".join(followers)
    # 经营分：月份聚合常为 -1，优先用短周期窗口补到的真实分
    if score_override not in (None, -1, 0):
        score = score_override
    else:
        s = rec.get("merchant_manage_score")
        score = s if isinstance(s, (int, float)) and s > 0 else 0
    return {
        "id": rec.get("merchant_id"),
        "name": rec.get("life_account_name"),
        "industry": rec.get("industry_name"),
        "category": rec.get("merchant_industry"),
        "mode": service,
        "follower": followers,
        "score": score,
        "pay": pay,
        "verified": verified,
        "refund": refund,
        "video": _safe(rec.get("indirect_item_pay_amount")),
        "live": _safe(rec.get("room_pay_amount")),
        "commission": _safe(rec.get("ledger_commission")),
        "providerCommission": _safe(rec.get("ledger_smc_commission")),
        "promoCost": _safe(rec.get("ledger_talent_commission")),
        "verifyRate": verify_rate,
        "refundRate": refund_rate,
    }


def fetch_array(ld_inst, start, end, account_id=DEFAULT_ACCOUNT_ID, ac_app=DEFAULT_AC_APP, timeout=45):
    """页面内 fetch 直连 list_panel，返回归一化前的原始记录数组。"""
    js = (
        "return (async function(){"
        "var accountId=" + json.dumps(account_id) + ", ac_app=" + json.dumps(ac_app) + ";"
        "var start=" + json.dumps(start) + ", end=" + json.dumps(end) + ";"
        "var r = await fetch('/data/life_partner/center/merchant/v3/list_panel?ac_app='+ac_app+'&accountId='+accountId, {"
        "  method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},"
        "  body: JSON.stringify({data_type:'all_merchant_cnt', page:1, limit:200, start_date:start, end_date:end})"
        "});"
        "var j = await r.json();"
        "return Array.isArray(j.data) ? j.data : (j.data && j.data.data) || [];"
        "})();"
    )
    return ld_inst.eval(js, timeout=timeout) or []


def fetch_merchants(ld_inst, start, end, account_id=DEFAULT_ACCOUNT_ID, ac_app=DEFAULT_AC_APP,
                    score_window=DEFAULT_SCORE_WINDOW, timeout=45):
    """拉取 [start, end] 区间全量商家并归一化；额外用当月 17~23 日窗口补经营分后合并。

    start/end 形如 'YYYY-MM-DD'（建议为完整自然月 1 日~月末）。
    返回归一化记录列表（每个含 score 已尽力补真实分）。
    """
    # 推导年份月份用于经营分窗口
    try:
        y, m = map(int, start.split("-")[:2])
    except Exception:
        y = m = None
    score_rows = []
    if y and m:
        last = calendar.monthrange(y, m)[1]
        sw_a = score_window[0] if score_window[0] <= last else last
        sw_b = score_window[1] if score_window[1] <= last else last
        sw_start = f"{y:04d}-{m:02d}-{sw_a:02d}"
        sw_end = f"{y:04d}-{m:02d}-{sw_b:02d}"
        # 窗口必须落在 [start, end] 内（字符串可比）
        if sw_start < start:
            sw_start = start
        if sw_end > end:
            sw_end = end
        if sw_end >= sw_start:
            score_rows = fetch_array(ld_inst, sw_start, sw_end, account_id, ac_app, timeout)
    rows = fetch_array(ld_inst, start, end, account_id, ac_app, timeout)
    score_map = {}
    for r in score_rows:
        mid = r.get("merchant_id")
        s = r.get("merchant_manage_score")
        if mid and isinstance(s, (int, float)) and s > 0:
            score_map[mid] = s
    return [transform(r, score_map.get(r.get("merchant_id"))) for r in rows]


def build_month_snapshot(list_, ym, start, end, saved_at=None):
    """构造一份历史快照 dict（与 data/history/{yyyy-MM}.json 形状一致）。"""
    return {
        "key": f"month:{ym}",
        "label": f"{start} ～ {end}",
        "statTime": f"{start} ～ {end}",
        "count": len(list_ or []),
        "list": list_ or [],
        "savedAt": saved_at or datetime.datetime.now().isoformat(timespec="seconds"),
    }


def main(argv=None):
    import argparse
    import os
    p = argparse.ArgumentParser(description="林客商家数据 API 直连取数（单月测试）")
    p.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    p.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    p.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
    p.add_argument("--ac-app", default=DEFAULT_AC_APP)
    p.add_argument("--out", default=None, help="输出 JSON 路径（不指定则打印摘要）")
    args = p.parse_args(argv)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ld  # noqa: E402
    inst = ld.LD(target_hint="life-partner")
    recs = fetch_merchants(inst, args.start, args.end, args.account_id, args.ac_app)
    print(f"[OK] {args.start}~{args.end} 共 {len(recs)} 家；首商家={recs[0]['name'] if recs else 'NONE'}")
    if args.out:
        snap = build_month_snapshot(recs, args.start[:7], args.start, args.end)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        print(f"[写出] {args.out}")
    else:
        for r in recs[:5]:
            print("  -", r["name"], "经营分", r["score"], "支付GMV", r["pay"])


if __name__ == "__main__":
    main()
