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


def set_page_size(ld_inst, size=100):
    """把每页条数调到 size（优先 100，其次 50），减少翻页次数。
    新版林客页大小是 byted-select，需要真实鼠标点开下拉再选选项。best-effort。"""
    js = r"""
    return (function(){
      var selects=[].slice.call(document.querySelectorAll('.byted-select'));
      for(var i=0;i<selects.length;i++){
        var s=selects[i];
        var val=s.querySelector('.byted-select-value');
        if(val && /条\/页/.test(val.value||'')){
          var r=val.getBoundingClientRect();
          return {x:r.x+r.width/2, y:r.y+r.height/2, current:val.value};
        }
      }
      return null;
    })();
    """
    info = ld_inst.eval(js)
    if not (info and isinstance(info, dict)):
        return False
    print(f"[分页] 当前每页条数: {info.get('current')}", flush=True)
    ld_inst._click_at(info["x"], info["y"])
    time.sleep(0.8)
    # 兼容多种选项 class
    opt_js = (
        "return (function(){"
        "var opts=[].slice.call(document.querySelectorAll('.byted-select-dropdown-item, .byted-select-dropdown-option, .byted-select-option, .byted-select-item'));"
        "for(var i=0;i<opts.length;i++){"
        "  if((opts[i].textContent||'').trim()===" + json.dumps(f"{size}条/页") + "){"
        "    var r=opts[i].getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2};"
        "  }"
        "}"
        "return null;})();"
    )
    opt = ld_inst.eval(opt_js)
    if opt and isinstance(opt, dict):
        ld_inst._click_at(opt["x"], opt["y"])
        time.sleep(1.5)
        return True
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


def _read_preview(ld_inst):
    """读取日期选择器预览文本，例如 '2026-08-01 ～ 2026-08-23'。"""
    js = r"""
    return (function(){
      var d=document.querySelector('.dd-advanced-date-picker-preview-content');
      if(d) return (d.textContent||'').trim();
      return null;
    })();
    """
    return ld_inst.eval(js)


def _click_custom_time(ld_inst):
    """真实鼠标点击「自定义时间」标签以打开双月日历弹层。"""
    js = r"""
    return (function(){
      var all=[].slice.call(document.querySelectorAll('*'));
      for(var i=0;i<all.length;i++){
        var e=all[i];
        if(e.children.length===0 && e.textContent.trim()==='自定义时间'){
          var r=e.getBoundingClientRect();
          return {x:r.x+r.width/2, y:r.y+r.height/2};
        }
      }
      return null;
    })();
    """
    rect = ld_inst.eval(js)
    if not (rect and isinstance(rect, dict)):
        print("[自定义] 找不到「自定义时间」入口", flush=True)
        return False
    ld_inst._click_at(rect["x"], rect["y"])
    return True


def _find_date_cell(ld_inst, year, month, day):
    """在已打开的双月日历中定位指定月份+日期的坐标（排除 prev/next 月日格）。"""
    label = f"{year}年{month}月"
    js = (
        "return (function(){"
        "var label=" + json.dumps(label) + ";"
        "var day=" + str(day) + ";"
        "function cls(e){ return e.getAttribute ? (e.getAttribute('class')||'') : ''; }"
        "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
        "for(var v=0;v<views.length;v++){"
        "  var view=views[v];"
        "  var header=(view.querySelector('.byted-date-nav-center')||view.querySelector('.byted-date-nav')).textContent||'';"
        "  if(header.replace(/\\s+/g,'').indexOf(label.replace(/\\s+/g,''))>=0){"
        "    var cells=[].slice.call(view.querySelectorAll('.byted-date-item'));"
        "    for(var i=0;i<cells.length;i++){"
        "      var e=cells[i];"
        "      var c=cls(e);"
        "      if((e.textContent||'').trim()===String(day) && c.indexOf('byted-date-grid-prev')<0 && c.indexOf('byted-date-grid-next')<0){"
        "        var r=e.getBoundingClientRect();"
        "        return {x:r.x+r.width/2, y:r.y+r.height/2, cls:c};"
        "      }"
        "    }"
        "  }"
        "}"
        "return null;"
        "})();"
    )
    return ld_inst.eval(js)


def _click_date(ld_inst, year, month, day):
    pos = _find_date_cell(ld_inst, year, month, day)
    if not pos:
        return 'notfound'
    ld_inst._click_at(pos["x"], pos["y"])
    return 'clicked'


def _ensure_month_visible(ld_inst, year, month, max_steps=30):
    """翻动双月日历直到目标月份出现在任一面板中。
    2026-08-21：新版林客箭头/标题的点击事件较特殊，目前优先靠 URL startDate/endDate
    设置周期；此函数作为日历兜底。"""
    label = f"{year}年{month}月"
    js_check = (
        "return (function(){"
        "var label=" + json.dumps(label) + ";"
        "var views=[].slice.call(document.querySelectorAll('.byted-date-view'));"
        "var headers=views.map(function(v){"
        "  var h=v.querySelector('.byted-date-nav-center')||v.querySelector('.byted-date-nav');"
        "  return (h?h.textContent:'').replace(/\\s+/g,'');"
        "});"
        "return headers.some(function(h){ return h.indexOf(label.replace(/\\s+/g,''))>=0; });"
        "})();"
    )
    for _ in range(max_steps):
        found = ld_inst.eval(js_check)
        if found:
            return True
        # 历史月份需要回退：先点左面板单月回退箭头，再尝试点标题
        nav_js = r"""
        return (function(){
          var leftView=document.querySelector('.byted-date-view');
          if(!leftView) return 'no-view';
          var arrow=leftView.querySelector('.byted-date-nav-prev .byted-icon-left');
          if(arrow){ arrow.parentElement.click(); return 'clicked-arrow'; }
          var title=leftView.querySelector('.byted-date-title');
          if(title){ title.click(); return 'clicked-title'; }
          return 'no-control';
        })();
        """
        res = ld_inst.eval(nav_js)
        if res == "no-view":
            return False
        time.sleep(0.7)
    return False


def set_custom_period(ld_inst, start, end):
    """新版林客商家数据页「自定义时间」统计周期（2026-08-21 适配）。
    start/end 形如 '2026-07-01' / '2026-07-31'。best-effort，返回 (start_res, end_res)。"""
    y1, m1, d1 = map(int, start.split('-'))
    y2, m2, d2 = map(int, end.split('-'))

    # 兜底 1：打开自定义时间弹层
    if not _click_custom_time(ld_inst):
        return (None, None)
    time.sleep(2.2)

    # 兜底 2：确保月份可见
    if not _ensure_month_visible(ld_inst, y1, m1):
        print(f"[自定义] 无法定位开始月份 {y1}-{m1:02d}", flush=True)
        return ("month-not-found", "month-not-found")
    if (y2, m2) != (y1, m1):
        _ensure_month_visible(ld_inst, y2, m2)

    r1 = _click_date(ld_inst, y1, m1, d1)
    time.sleep(0.6)
    r2 = _click_date(ld_inst, y2, m2, d2)
    time.sleep(0.8)

    # 关闭弹层让选中生效
    ld_inst.eval("document.body.click();")
    time.sleep(0.6)

    preview = _read_preview(ld_inst)
    ok = preview and start in preview and end in preview
    print(f"[自定义] 周期 {start} ~ {end}（开始:{r1} 结束:{r2}）预览={preview} 验证={'OK' if ok else 'FAIL'}", flush=True)
    return (r1, r2)


def navigate(ld_inst, tab, period, start=None, end=None):
    """导航到 商家数据→商家列表，设时间（预设或自定义），切子 tab。
    2026-08-21 修正：
      - 新版林客首页把内容放在 iframe/summon 里，直接跳转到商家数据 SPA 路由。
      - 自定义周期优先通过 URL startDate/endDate 设置（生意经同款参数名），
        若页面未生效再用双月日历兜底。"""
    target_url = "https://www.life-partner.cn/subapp/dp-life-service-provider-pro/businessData?from_page=merchant_operation"
    if start and end:
        target_url += f"&startDate={start}&endDate={end}"

    current = ld_inst.eval("return window.location.href") or ""
    need_nav = "businessData" not in current
    if start and end:
        need_nav = need_nav or f"startDate={start}" not in current or f"endDate={end}" not in current

    if need_nav:
        ld_inst.eval(f"window.location.href = {json.dumps(target_url)}")
        print(f"[导航] 跳转至商家数据页：{target_url}", flush=True)
        time.sleep(4.0)
    else:
        print(f"[导航] 已在商家数据页：{current}", flush=True)

    # 1) 顶部 Tab 商家列表
    ld_inst.click_text("商家列表")
    time.sleep(1.5)

    # 2) 时间：自定义周期优先 URL 参数；未生效再用日历兜底
    if start and end:
        preview = _read_preview(ld_inst)
        if preview and start in preview and end in preview:
            print(f"[导航] URL 参数已生效，周期={preview}", flush=True)
        else:
            print("[导航] URL 参数未生效，使用日历兜底", flush=True)
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

    # 2026-08-21 修正：优先把每页条数调到 100（或 50），尽量一页抓全 84 家，降低翻页失败概率
    page_size_ok = False
    for size in (100, 50):
        print(f"[分页] 尝试设置每页 {size} 条...", flush=True)
        if set_page_size(ld_inst, size):
            page_size_ok = True
            break
    if not page_size_ok:
        print("[分页] 无法切换每页条数，将保持 10 条/页并尝试翻页", flush=True)

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
