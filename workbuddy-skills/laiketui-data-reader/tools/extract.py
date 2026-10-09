#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reusable 生意经 (life-data) extraction helpers built on ld.py.
All data is scraped for 新海府 (groupid 1736233383495694) for a given date range.
"""
import json
import ld


def cards(L):
    """Extract all .dd-measure-card as [{name, prefix, value, delta}]."""
    return L.eval(r"""
    function clean(t){return (t||'').replace(/\s+/g,' ').trim();}
    var cards=[].slice.call(document.querySelectorAll('.dd-measure-card'));
    return cards.map(function(c){
      var name=(c.querySelector('.dd-measure-card-header-name')||{}).textContent||'';
      var pre=(c.querySelector('.dd-measure-value-prefix')||{}).textContent||'';
      var val=(c.querySelector('.dd-measure-value')||{}).textContent||'';
      var delta='';
      var vpc=c.querySelector('.dd-measure-value-primary-content');
      if(vpc && vpc.nextElementSibling) delta=clean(vpc.nextElementSibling.textContent);
      return {name:clean(name), prefix:clean(pre), value:clean(val), delta:delta};
    });
    """)


def card_map(L):
    """cards() keyed by name -> value (with prefix), keeping delta too."""
    out = {}
    for d in cards(L):
        out[d["name"]] = {"value": d["prefix"] + d["value"], "delta": d["delta"]}
    return out


def tables(L):
    """Extract all <table> blocks as list of rows (each row = list of cell texts)."""
    return L.eval(r"""
    function clean(t){return (t||'').replace(/\s+/g,' ').trim();}
    var tbls=[].slice.call(document.querySelectorAll('table'));
    return tbls.map(function(t){
      var rows=[].slice.call(t.querySelectorAll('tr'));
      return rows.map(function(r){
        var cells=[].slice.call(r.querySelectorAll('th,td'));
        return cells.map(function(c){return clean(c.textContent);});
      });
    });
    """)


def set_july(L):
    return L.set_range(2026, 7, 1, 2026, 7, 31)


def go_module(L, name):
    L.click_text(name)
    L.wait(1800)
    set_july(L)
    L.wait(500)


def click_subpage(L, name):
    """Click a sidebar sub-page (内容分析/搜索分析/门店页流量/商品概览/人群资产...)."""
    L.click_text(name)
    L.wait(1800)
    set_july(L)
    L.wait(500)


if __name__ == "__main__":
    L = ld.LD()
    # quick smoke test
    go_module(L, "经营")
    print("经营 金额:", json.dumps(card_map(L), ensure_ascii=False))
