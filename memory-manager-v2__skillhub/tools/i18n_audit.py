#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n 键覆盖审计（5.2）。

扫描 memory_manager/*.py 中所有 _("key") / _('key') 的字面量调用，
比对 i18n.json 的 zh / en 键集：
  - 代码使用但 i18n 缺失的键  → 原始 key 泄漏风险（必须修复）
  - zh / en 键集不一致         → 双语不对齐
  - (--strict) i18n 中存在但代码未使用的键 → 冗余（可选报错）

发现问题时返回非零退出码，供 CI / pre-commit 拦截。

用法:
    python tools/i18n_audit.py [--root <repo-root>] [--strict]
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 匹配 _("key") 或 _('key') 的字面量 key（不含括号内的变量/表达式）
KEY_RE = re.compile(r'_\([\'"]([^\'")]+)[\'"]\)')


def scan_used_keys(root: Path):
    """遍历 memory_manager/*.py，收集所有字面量 i18n key。"""
    used = set()
    py_files = list((root / "memory_manager").rglob("*.py"))
    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in KEY_RE.finditer(text):
            used.add(m.group(1))
    return used, py_files


def main():
    ap = argparse.ArgumentParser(description="i18n key coverage audit")
    ap.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="仓库根目录（含 i18n.json 与 memory_manager/），默认脚本上级目录",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="同时把『i18n 中未使用键』视为错误",
    )
    args = ap.parse_args()
    root = Path(args.root)

    i18n_path = root / "i18n.json"
    if not i18n_path.exists():
        print(f"\u274c i18n.json 未找到: {i18n_path}")
        return 1
    try:
        data = json.loads(i18n_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"\u274c i18n.json 解析失败: {e}")
        return 1

    zh = set(data.get("zh", {}))
    en = set(data.get("en", {}))
    used, py_files = scan_used_keys(root)

    errors = []  # (label, [keys])

    missing_zh = sorted(k for k in used if k not in zh)
    missing_en = sorted(k for k in used if k not in en)
    if missing_zh:
        errors.append(("\u7f3a\u5931(zh)", missing_zh))
    if missing_en:
        errors.append(("\u7f3a\u5931(en)", missing_en))

    only_zh = sorted(zh - en)
    only_en = sorted(en - zh)
    if only_zh:
        errors.append(("\u4ec5zh\u5b58\u5728", only_zh))
    if only_en:
        errors.append(("\u4ec5en\u5b58\u5728", only_en))

    if args.strict:
        unused = sorted((zh | en) - used)
        if unused:
            errors.append(("\u672a\u4f7f\u7528", unused))

    print(
        f"\u626b\u63cf: {len(py_files)} \u4e2a .py | \u4f7f\u7528\u952e: {len(used)} | "
        f"zh: {len(zh)} | en: {len(en)}"
    )

    if not errors:
        print("\u2705 i18n \u952e\u8986\u76d6\u5b8c\u6574\uff0czh/en \u4e00\u81f4\u3002")
        return 0

    for label, keys in errors:
        shown = ", ".join(keys[:30])
        if len(keys) > 30:
            shown += " ..."
        print(f"\u274c {label} ({len(keys)}): {shown}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
