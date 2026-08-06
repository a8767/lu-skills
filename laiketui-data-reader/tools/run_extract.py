#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harvest 新海府 July data from 生意经 into july_data.json (incremental)."""
import json
import ld
import extract as E

OUT = "E:/AI助理/2026-08-05-13-51-38/july_data.json"


def load():
    try:
        return json.load(open(OUT, encoding="utf-8"))
    except Exception:
        return {}


def save(d):
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def verify(L, label):
    p = L.period_text()
    ok = bool(p and "2026-07-01" in (p or "") and "2026-07-31" in (p or ""))
    print(f"  [{label}] period={p} ok={ok}")
    return ok


DATA = load()
L = ld.LD()

# ---------- 1. 经营概览 (金额/券数/人数) ----------
try:
    E.go_module(L, "经营")
    verify(L, "经营")
    biz = {}
    for tab in ["金额", "券数", "人数"]:
        try:
            L._click_preset(tab)
        except Exception:
            pass
        L.wait(900)
        biz[tab] = E.card_map(L)
    DATA["经营概览"] = biz
    save(DATA)
    print("经营概览 done:", json.dumps(biz, ensure_ascii=False)[:300])
except Exception as e:
    print("经营概览 ERR:", e)

# ---------- 2. 流量概览 (曝光) ----------
try:
    E.go_module(L, "流量")
    verify(L, "流量概览")
    DATA["流量概览"] = E.card_map(L)
    save(DATA)
    print("流量概览 done")
except Exception as e:
    print("流量概览 ERR:", e)

# ---------- 3. 门店页流量 (访问) ----------
try:
    L.click_text("门店页流量")
    L.wait(1800)
    E.set_july(L)
    L.wait(500)
    verify(L, "门店页流量")
    DATA["门店页流量"] = E.card_map(L)
    save(DATA)
    print("门店页流量 done")
except Exception as e:
    print("门店页流量 ERR:", e)

# ---------- 4. 商品概览 (cards + TOP5 table) ----------
try:
    E.go_module(L, "商品")
    verify(L, "商品")
    DATA["商品概览"] = E.card_map(L)
    DATA["商品表格"] = E.tables(L)
    save(DATA)
    print("商品 done; tables:", len(DATA["商品表格"]))
except Exception as e:
    print("商品 ERR:", e)

# ---------- 5. 搜索分析 ----------
try:
    E.go_module(L, "流量")  # context for sidebar
    L.click_text("搜索分析")
    L.wait(1800)
    E.set_july(L)
    L.wait(500)
    verify(L, "搜索分析")
    DATA["搜索分析_cards"] = E.card_map(L)
    DATA["搜索分析_tables"] = E.tables(L)
    save(DATA)
    print("搜索分析 done")
except Exception as e:
    print("搜索分析 ERR:", e)

# ---------- 6. 内容分析 (直播/视频) ----------
try:
    E.go_module(L, "流量")
    L.click_text("内容分析")
    L.wait(1800)
    E.set_july(L)
    L.wait(500)
    verify(L, "内容分析")
    DATA["内容分析_cards"] = E.card_map(L)
    DATA["内容分析_tables"] = E.tables(L)
    save(DATA)
    print("内容分析 done")
except Exception as e:
    print("内容分析 ERR:", e)

# ---------- 7. 人群资产 ----------
try:
    E.go_module(L, "人群")
    verify(L, "人群")
    DATA["人群资产_cards"] = E.card_map(L)
    DATA["人群资产_tables"] = E.tables(L)
    save(DATA)
    print("人群资产 done")
except Exception as e:
    print("人群资产 ERR:", e)

print("\n=== SAVED july_data.json ===")
print(json.dumps(DATA, ensure_ascii=False)[:200])
