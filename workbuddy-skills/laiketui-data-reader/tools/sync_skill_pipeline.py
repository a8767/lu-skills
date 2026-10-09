#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_skill_pipeline.py — 林客数据读取链路「自动同步」生成器（skill 内）

职责：以 tools/fetch_list_panel.py 为**唯一真理来源**，重新生成 references/data-pipeline.md，
保证「文档规范」与「代码链路」永不漂移。

为什么需要它（满足"流程优化时自动同步、无需手动干预"）：
- fetch_list_panel.py 是取数链路唯一实现（PIPELINE_VERSION + SPEC 常量）。
- data-pipeline.md 由本脚本从 SPEC 自动生成，**禁止手工编辑**。
- 优化链路 = 改 fetch_list_panel.py（单一处）→ 运行本脚本（或由每日自动化运行）→
  data-pipeline.md 自动更新；同时 workbench 等消费方直接 import 该模块，运行时也自动跟随最新。
  → skill 内部逻辑始终反映最新链路设计，无需手动拷贝。

运行：
    python sync_skill_pipeline.py
（建议由每日自动化「林客数据链路自动同步」调用，无需人工介入）

退出码：0=成功/无变更；2=模块导入失败（不覆盖旧文档）；1=写文件失败。
"""
import hashlib
import os
import sys
import datetime

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(TOOLS_DIR)
SPEC_PATH = os.path.join(SKILL_ROOT, "references", "data-pipeline.md")
LOG_PATH = os.path.join(TOOLS_DIR, "_pipeline_sync.log")


def log(msg):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    if TOOLS_DIR not in sys.path:
        sys.path.insert(0, TOOLS_DIR)

    # 1) 导入自检：模块必须能正常 import 才允许同步（避免坏代码覆盖好文档）
    try:
        import fetch_list_panel as fpl  # noqa: E402
    except Exception as e:
        log(f"[ABORT] 无法 import fetch_list_panel：{e}")
        sys.exit(2)

    version = getattr(fpl, "PIPELINE_VERSION", "?.?.?")
    spec = getattr(fpl, "SPEC", "")
    if not spec:
        log("[ABORT] fetch_list_panel.SPEC 为空，中止同步")
        sys.exit(2)

    # 2) 组装文档内容
    header = (
        "# 林客商家数据读取链路规范（Data-Reading Pipeline Spec）\n\n"
        f"> **本文件由 `tools/sync_skill_pipeline.py` 自动生成自 `tools/fetch_list_panel.py`"
        f"（PIPELINE_VERSION={version}）。请勿手工编辑——修改链路后运行同步脚本重新生成。**\n\n"
        "---\n\n"
    )
    content = header + spec

    # 3) 变更比对：仅在内容变化时才落盘，避免无谓写入
    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    old_hash = None
    if os.path.exists(SPEC_PATH):
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            old = f.read()
        old_hash = hashlib.sha256(old.encode("utf-8")).hexdigest()[:16]

    if old_hash == new_hash:
        log(f"[OK] data-pipeline.md 已是最新（PIPELINE_VERSION={version}，hash={new_hash}），无需更新")
        # 仍做一次 SKILL.md 引用检查
        _check_skill_reference()
        sys.exit(0)

    # 4) 落盘
    try:
        os.makedirs(os.path.dirname(SPEC_PATH), exist_ok=True)
        with open(SPEC_PATH, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        log(f"[FAIL] 写入 data-pipeline.md 失败：{e}")
        sys.exit(1)

    log(f"[SYNC] 已重新生成 data-pipeline.md（PIPELINE_VERSION={version}，hash={new_hash}，原hash={old_hash}）")
    _check_skill_reference()
    sys.exit(0)


def _check_skill_reference():
    """检查 SKILL.md 是否引用了 data-pipeline.md；缺失则提示（不自动改 SKILL.md，避免误伤）。"""
    skill_md = os.path.join(SKILL_ROOT, "SKILL.md")
    if not os.path.exists(skill_md):
        return
    try:
        txt = open(skill_md, "r", encoding="utf-8").read()
    except Exception:
        return
    if "data-pipeline.md" in txt:
        log("[OK] SKILL.md 已引用 data-pipeline.md")
    else:
        log("[WARN] SKILL.md 未引用 data-pipeline.md，请补充 4.8 节引用")


if __name__ == "__main__":
    main()
