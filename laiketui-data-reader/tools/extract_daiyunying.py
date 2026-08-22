#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_daiyunying.py - 抖音林客 → 商家数据 → 商家列表 全量代运营商家采集

真实页面结构（2026-08-15 实测 life-partner.cn）：
    - 左侧菜单「商家数据」
    - 顶部 Tab「商家概览 / 商家分析 / 商家列表」（截图里的"探索列表"在本账号实为"商家列表"）
    - 子筛选 Tab：全部商家 / 服务中商家 / 无动销商家 / 新签商家 / 取消合作商家
    - 时间预设：今日实时 / 近1天 / 近7天 / 近30天 / 本月 / 自定义
    - 表格为 div 结构（class 前缀 lifep-table），非原生 <table>
    - 表头：.lifep-table-header-content-title
    - 数据行：.lifep-table-row（排除含 header-title 的表头行），单元格 .lifep-table-cell
    - 分页：.lifep-table-pagination 内 .byted-pager-item（下一页=最后一个 item，图标按钮）

核心字段（14 列，用户关注加粗）：
    商家名称(含商家ID) / 行业 / 合作模式 / 类目 / 跟进人 / 商家经营分 /
    支付GMV / 核销GMV / 退款GMV / 视频直接支付GMV / 直播支付GMV /
    总预估佣金 / 服务商预估佣金 / 操作
    衍生：核销率 / 退款率 / 推广佣金成本(=总预估佣金-服务商预估佣金)

用法：
    python extract_daiyunying.py
        # 默认：全部商家 + 本月（本月至今）+ out/代运营_<时间>.csv
    python extract_daiyunying.py --tab 服务中商家 --period 近7天
    python extract_daiyunying.py --tab 全部商家 --period 本月
    python extract_daiyunying.py --out "代运营_2026-08.csv"

作者：基于 laiketui-data-reader 扩展（2026-08-15 重写以适配真实 lifep-table DOM）。
"""
import argparse
import csv
import json
import os
import re
import sys
import time

# 复用 ld.py 的 LD 类（已最小改动支持 target_hint）
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "tools"))
import ld  # noqa: E402


# 列名 → 标准键 映射（顺序即表头顺序）
COLUMN_MAP = {
    "商家名称": "merchant_name",
    "行业": "industry",
    "合作模式": "cooperation_mode",
    "类目": "category",
    "跟进人": "follower",
    "商家经营分": "business_score",
    "支付GMV": "pay_gmv",
    "核销GMV": "verified_gmv",
    "退款GMV": "refund_gmv",
    "视频直接支付GMV": "video_pay_gmv",
    "直播支付GMV": "live_pay_gmv",
    "总预估佣金": "total_est_commission",
    "服务商预估佣金": "provider_est_commission",
}


def parse_amount(s):
    """把 '¥128.05万' / '8,261元' / '70.13万' 转为元（浮点，round 2 位）。"""
    if s is None:
        return None
    t = str(s).strip().replace("¥", "").replace(",", "").replace(" ", "")
    if not t:
        return None
    unit = 1
    if t.endswith("万"):
        unit = 10000
        t = t[:-1]
    elif t.endswith("亿"):
        unit = 100000000
        t = t[:-1]
    m = re.match(r"^-?\d+(\.\d+)?$", t)
    if not m:
        return None
    return round(float(t) * unit, 2)


def parse_score(s):
    if s is None:
        return None
    t = str(s).strip()
    if not t or t == "-":
        return None
    m = re.match(r"^-?\d+(\.\d+)?$", t)
    return float(t) if m else None


def get_headers(ld_inst):
    """返回 14 列表头列名。"""
    js = r"""
    return [].slice.call(document.querySelectorAll('.lifep-table-header-content-title'))
        .map(function(e){return (e.textContent||'').trim();})
        .filter(function(t){return t.length>0;});
    """
    return ld_inst.eval(js) or []


def get_rows(ld_inst):
    """返回当前页数据行（二维数组），排除表头行。"""
    js = r"""
    function clean(c){return (c.textContent||'').replace(/\s+/g,' ').trim();}
    var rows=[].slice.call(document.querySelectorAll('.lifep-table-row'));
    var data=[];
    rows.forEach(function(r){
      if(r.querySelector('.lifep-table-header-content-title')) return; // 表头行跳过
      var cells=[].slice.call(r.querySelectorAll('.lifep-table-cell')).map(clean);
      if(cells.length>=10) data.push(cells);
    });
    return data;
    """
    return ld_inst.eval(js) or []


def get_total_count(ld_inst):
    """读 '共85条记录' 中的数字。"""
    js = r"""
    var el=[].slice.call(document.querySelectorAll('*')).find(function(e){
      return /共\d+条记录/.test(e.textContent) && e.textContent.length<40;
    });
    if(!el) return null;
    var m=el.textContent.match(/共(\d+)条记录/);
    return m? parseInt(m[1],10):null;
    """
    return ld_inst.eval(js)


def get_checked_page(ld_inst):
    """读当前选中页码（.byted-pager-item-checked）。"""
    js = r"""
    var c=document.querySelector('.byted-pager-item-checked');
    return c? (parseInt((c.textContent||'').trim(),10)||1):1;
    """
    return ld_inst.eval(js) or 1


def get_stat_time(ld_inst):
    """读页面显示的统计时间范围，如 '2026-08-01 ～ 2026-08-15'。"""
    js = r"""
    var el=[].slice.call(document.querySelectorAll('*')).find(function(e){
      return /统计时间\s*[:：]/.test(e.textContent) && e.textContent.length<60;
    });
    if(!el) return null;
    var m=el.textContent.match(/统计时间\s*[:：]\s*([\d~～\-\s]+)/);
    return m? m[1].trim(): el.textContent.trim();
    """
    return ld_inst.eval(js)


def set_page_size(ld_inst, size=50):
    """把每页条数调到 size（10/20/50），减少翻页次数。best-effort，失败返回 False。"""
    try:
        ld_inst.click_text("10条/页")  # 打开页大小下拉（当前值）
    except Exception:
        pass
    time.sleep(0.8)
    try:
        ld_inst.click_text(f"{size}条/页")
        time.sleep(1.2)
        return True
    except Exception:
        return False


def click_next(ld_inst, retries=8):
    """点击下一页（.byted-pager-item 最后一个=下一页箭头）。
    2026-08-21 修正：增加 scrollIntoView + JS .click() 兜底，降低真实鼠标事件未命中概率。"""
    for _ in range(retries):
        js = r"""
        return (function(){
          var items=[].slice.call(document.querySelectorAll('.byted-pager-item'));
          if(!items.length) return null;
          var next=items[items.length-1];
          if(next.disabled || (next.getAttribute('class')||'').indexOf('disabled')>=0) return 'disabled';
          next.scrollIntoView({block:'nearest',inline:'nearest'});
          var r=next.getBoundingClientRect();
          if(!r.width && !r.height) return null;
          return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2), el:true};
        })()
        """
        pos = ld_inst.eval(js)
        if pos == "disabled":
            return False
        if pos and "x" in pos:
            ld_inst._send("Input.dispatchMouseEvent",
                          {"type": "mouseMoved", "x": pos["x"], "y": pos["y"], "modifiers": 0}, timeout=10)
            for typ in ("mousePressed", "mouseReleased"):
                ld_inst._send("Input.dispatchMouseEvent",
                              {"type": typ, "x": pos["x"], "y": pos["y"],
                               "button": "left", "clickCount": 1, "modifiers": 0}, timeout=10)
            return True
        # fallback: 直接用 JS click
        fallback = ld_inst.eval("(function(){var items=[].slice.call(document.querySelectorAll('.byted-pager-item')); if(!items.length) return 'no-items'; var next=items[items.length-1]; if(next.disabled) return 'disabled'; next.scrollIntoView(); next.click(); return 'clicked';})()")
        if fallback in ("clicked",):
            return True
        if fallback == "disabled":
            return False
        time.sleep(0.4)
    return False


def goto_page1(ld_inst):
    """翻页可能残留到非第1页，先点回第1页，确保从头部采集。"""
    js = r"""
    return (function(){
      var its=[].slice.call(document.querySelectorAll('.byted-pager-item'));
      for(var i=0;i<its.length;i++){
        if((its[i].textContent||'').trim()==='1'){
          var r=its[i].getBoundingClientRect();
          if(!r.width && !r.height) return null;
          return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
        }
      }
      return null;
    })()
    """
    for _ in range(3):
        p = ld_inst.eval(js)
        if p and "x" in p:
            ld_inst._send("Input.dispatchMouseEvent",
                          {"type": "mouseMoved", "x": p["x"], "y": p["y"], "modifiers": 0}, timeout=10)
            for typ in ("mousePressed", "mouseReleased"):
                ld_inst._send("Input.dispatchMouseEvent",
                              {"type": typ, "x": p["x"], "y": p["y"],
                               "button": "left", "clickCount": 1, "modifiers": 0}, timeout=10)
            return True
        time.sleep(0.4)
    return False


def harvest_all_pages(ld_inst, max_pages=20):
    """循环翻页采集所有数据行，按商家名称去重。翻页后等待表格真正刷新再读。"""
    total = get_total_count(ld_inst) or 0
    print(f"[分页] 商家总数={total}", flush=True)
    all_rows = []
    seen = set()
    last_sig = None
    for page in range(1, max_pages + 1):
        time.sleep(1.0)
        rows = get_rows(ld_inst)
        new = 0
        for r in rows:
            sig = r[0] if r else ""
            if sig in seen:
                continue
            seen.add(sig)
            all_rows.append(r)
            new += 1
        cur = get_checked_page(ld_inst)
        print(f"[第{cur}页] +{new} 行（累计 {len(all_rows)}）", flush=True)
        if total and len(all_rows) >= total:
            break
        pre_first = rows[0][0] if rows else None
        if not click_next(ld_inst):
            print("[翻页] 找不到下一页按钮，停止", flush=True)
            break
        # 等表格真正刷新：页码变化 且 首行商家变化（最多 ~12s）
        refreshed = False
        for _ in range(30):
            time.sleep(0.4)
            nxt = get_checked_page(ld_inst)
            rows2 = get_rows(ld_inst)
            sig2 = rows2[0][0] if rows2 else ""
            page_changed = nxt != cur
            data_changed = sig2 and pre_first and sig2 != pre_first
            if page_changed and data_changed:
                refreshed = True
                break
            # 容错：页码确实变了且超过 4s 仍没新数据，也继续（有些页可能为空或 API 慢）
            if page_changed and _ >= 10:
                refreshed = True
                break
        if not refreshed:
            print("[翻页] 页码/数据未刷新，停止", flush=True)
            break
    return all_rows, total


def set_custom_period(ld_inst, start, end):
    """林客商家数据页「自定义」统计周期：
    点自定义 → 双月日历选 start~end 日期格（跨月先起后止）→ 点「确定」。
    start/end 形如 '2026-07-01' / '2026-07-31'。best-effort，返回 (start_res, end_res)。"""
    try:
        ld_inst.click_text("自定义")
    except Exception:
        print("[自定义] 找不到「自定义」入口", flush=True)
        return (None, None)
    time.sleep(1.8)

    def click_day(day_str):
        # 林客日历日格 className 含 byted-date-date / byted-date-item
        js = r"""
        var target=%s;
        var day=String(parseInt(target.split('-')[2],10));
        var cells=[].slice.call(document.querySelectorAll('.byted-date-date, .byted-date-item'));
        for(var i=0;i<cells.length;i++){
          var c=cells[i];
          if((c.textContent||'').trim()===day){
            var r=c.getBoundingClientRect();
            if(r.width||r.height){
              c.scrollIntoView({block:'center'});
              // byted 日期格需要真实鼠标事件才能触发 onClick
              window.__lt={x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};
              return 'found';
            }
          }
        }
        return 'notfound';
        """ % json.dumps(day_str)
        r = ld_inst.eval(js)
        if r != 'found':
            return r
        pos = ld_inst.eval("window.__lt")
        if not pos:
            return 'no-pos'
        for typ in ("mouseMoved", "mousePressed", "mouseReleased"):
            ld_inst._send("Input.dispatchMouseEvent",
                          {"type": typ, "x": pos["x"], "y": pos["y"],
                           "button": "left", "clickCount": 1, "modifiers": 0}, timeout=10)
        time.sleep(0.3)
        return 'clicked'

    r1 = click_day(start)
    time.sleep(0.9)
    r2 = click_day(end)
    time.sleep(0.9)
    try:
        ld_inst.click_text("确定")
    except Exception:
        print("[自定义] 未找到「确定」按钮", flush=True)
    time.sleep(1.5)
    print(f"[自定义] 周期 {start} ~ {end}（开始:{r1} 结束:{r2}）", flush=True)
    return (r1, r2)


def navigate(ld_inst, tab, period, start=None, end=None):
    """导航到 商家数据→商家列表，设时间（预设或自定义），切子 tab。
    2026-08-21 修正：新版林客首页把内容放在 iframe/summon 里，
    直接跳转到商家数据 SPA 路由，避免从首页点击菜单找不到表头。"""
    target_url = "https://www.life-partner.cn/subapp/dp-life-service-provider-pro/businessData?from_page=merchant_operation"
    current = ld_inst.eval("return window.location.href") or ""
    if "businessData" not in current:
        ld_inst.eval(f"window.location.href = {json.dumps(target_url)}")
        print(f"[导航] 跳转至商家数据页：{target_url}", flush=True)
        time.sleep(3.5)
    else:
        print(f"[导航] 已在商家数据页：{current}", flush=True)

    # 1) 顶部 Tab 商家列表
    ld_inst.click_text("商家列表")
    time.sleep(1.5)
    # 2) 时间：自定义周期 或 预设
    if start and end:
        set_custom_period(ld_inst, start, end)
    else:
        ld_inst.click_text(period)
        time.sleep(1.5)
    # 3) 子 tab（全部商家 等）
    ld_inst.click_text(tab)
    time.sleep(1.5)


def rows_to_records(headers, rows):
    """表头+行 → 结构化记录 + 衍生计算。"""
    records = []
    for r in rows:
        rec = {}
        for i, h in enumerate(headers):
            cell = r[i] if i < len(r) else ""
            key = COLUMN_MAP.get(h)
            if key is None:
                key = "col_" + re.sub(r"\W+", "_", h)
            rec[key] = cell
        # 商家ID 提取
        name = rec.get("merchant_name", "") or ""
        mid = re.search(r"商家ID[:：]\s*(\d+)", name)
        if mid:
            rec["merchant_id"] = mid.group(1)
            rec["merchant_name"] = re.sub(r"\s*商家ID[:：].*$", "", name).strip()
        # 数值化
        rec["pay_gmv_yuan"] = parse_amount(rec.get("pay_gmv"))
        rec["verified_gmv_yuan"] = parse_amount(rec.get("verified_gmv"))
        rec["refund_gmv_yuan"] = parse_amount(rec.get("refund_gmv"))
        rec["video_pay_gmv_yuan"] = parse_amount(rec.get("video_pay_gmv"))
        rec["live_pay_gmv_yuan"] = parse_amount(rec.get("live_pay_gmv"))
        rec["total_est_commission_yuan"] = parse_amount(rec.get("total_est_commission"))
        rec["provider_est_commission_yuan"] = parse_amount(rec.get("provider_est_commission"))
        rec["business_score_num"] = parse_score(rec.get("business_score"))
        # 衍生
        pay = rec["pay_gmv_yuan"] or 0
        if pay > 0:
            rec["verify_rate"] = round((rec["verified_gmv_yuan"] or 0) / pay, 4)
            rec["refund_rate"] = round((rec["refund_gmv_yuan"] or 0) / pay, 4)
        else:
            rec["verify_rate"] = None
            rec["refund_rate"] = None
        if rec["total_est_commission_yuan"] is not None and rec["provider_est_commission_yuan"] is not None:
            rec["promotion_cost_yuan"] = round(
                rec["total_est_commission_yuan"] - rec["provider_est_commission_yuan"], 2)
        else:
            rec["promotion_cost_yuan"] = None
        records.append(rec)
    return records


def main():
    p = argparse.ArgumentParser(description="林客·商家列表 全量代运营商家采集")
    p.add_argument("--tab", default="全部商家",
                   help="子tab：全部商家 / 服务中商家 / 无动销商家 / 新签商家 / 取消合作商家")
    p.add_argument("--period", default="本月",
                   help="时间预设：本月 | 近7天 | 近30天 | 近1天 | 今日实时")
    p.add_argument("--start", default=None, help="自定义周期开始日期 YYYY-MM-DD（与 --end 同用）")
    p.add_argument("--end", default=None, help="自定义周期结束日期 YYYY-MM-DD")
    p.add_argument("--out", default=None, help="输出 CSV 路径")
    p.add_argument("--max-pages", type=int, default=20)
    args = p.parse_args()

    try:
        ld_inst = ld.LD(target_hint="life-partner")
    except SystemExit as e:
        print(f"[错误] {e}", flush=True)
        print("  → 请确认 Edge 已登录抖音林客 life-partner.cn，调试端口 9223 已开启", flush=True)
        sys.exit(1)
    print(f"[连接] hint={ld_inst.hint} tid={ld_inst.tid}", flush=True)

    navigate(ld_inst, args.tab, args.period, start=args.start, end=args.end)
    time.sleep(1.0)

    headers = get_headers(ld_inst)
    if not headers:
        print("[错误] 找不到表头，请确认已进入 商家数据→商家列表 且表格已加载", flush=True)
        ld_inst.screenshot(os.path.join(SKILL_ROOT, "tools", "extract_daiyunying_err.png"))
        sys.exit(2)
    print(f"[表头] 共 {len(headers)} 列: {headers}", flush=True)

    stat_time = get_stat_time(ld_inst)
    print(f"[时间] 统计时间={stat_time}", flush=True)

    goto_page1(ld_inst)
    time.sleep(1.0)

    # 2026-08-21 修正：优先把每页条数调到 50，减少翻页次数，降低翻页失败概率
    print("[分页] 尝试设置每页 50 条...", flush=True)
    set_page_size(ld_inst, 50)

    rows, total = harvest_all_pages(ld_inst, max_pages=args.max_pages)
    print(f"[汇总] 采集 {len(rows)} 行（声明总数 {total}）", flush=True)

    records = rows_to_records(headers, rows)

    if args.out:
        out_path = args.out
    else:
        out_dir = os.path.join(SKILL_ROOT, "out")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"代运营_{args.tab}_{args.period}.csv")

    out_headers = (list(COLUMN_MAP.values()) +
                   ["pay_gmv_yuan", "verified_gmv_yuan", "refund_gmv_yuan",
                    "video_pay_gmv_yuan", "live_pay_gmv_yuan",
                    "total_est_commission_yuan", "provider_est_commission_yuan",
                    "business_score_num", "verify_rate", "refund_rate", "promotion_cost_yuan"])
    seen = set()
    final_headers = [h for h in out_headers if not (h in seen or seen.add(h))]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=final_headers, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"[写入] {out_path}  共 {len(records)} 行", flush=True)

    json_path = re.sub(r"\.csv$", ".json", out_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"stat_time": stat_time, "headers": headers,
                   "total": total, "records": records},
                  f, ensure_ascii=False, indent=2)
    print(f"[备份] {json_path}", flush=True)
    ld_inst.close()


if __name__ == "__main__":
    main()
