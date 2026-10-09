# -*- coding: utf-8 -*-
"""
记忆管家 V3.0 - CLI 命令处理器（_h_*）
从 cli_handlers.py 拆分，降低单文件长度（file>800 硬限 P1）。
共享辅助（_emit/_require_confirmation/_make_progress）来自 cli_handlers。
"""
import json

from .config import get_colors, _
from .cli_handlers import _emit, _require_confirmation, _make_progress
from .core import analyze_memory, search_memory, load_memory, rank_memory
from .summarize import summarize_memory
from .cache import cache_clean, cache_reminder
from .clean import (
    auto_clean_memory, archive_old_memory, dedup_memory,
    generate_cleanup_preview, scan_workspace, execute_cleanup,
)
from .io import export_memories, import_memories, backup_memory, restore_backup
from .report import (
    generate_memory_report, print_memory_analysis, print_preview, print_report,
)
from .token import token_check, token_trends, kb_to_tokens
from .prompt import list_prompts, get_prompt, save_prompt, search_prompts
from .cli_handlers import _handle_self_test


def _h_analyze(args):
    result = analyze_memory(args.workspace)
    print_memory_analysis(result, format_type="json" if getattr(args, 'json', False) else "text")
    return 0


def _h_search(args):
    C = get_colors()
    tag = getattr(args, 'tag', None)
    folder = getattr(args, 'folder', None)
    result = search_memory(args.workspace, args.keyword, tag=tag, folder=folder)
    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    tag_info = f" [tag={tag}]" if tag else ""
    folder_info = f" [folder={folder}]" if folder else ""
    print(f"\n{C['bright']}\U0001f50d 搜索结果: \"{args.keyword}\"{tag_info}{folder_info} ({result['total']} 个匹配){C['reset']}")
    for i, m in enumerate(result["matches"][:10], 1):
        tags_str = f" [{','.join(m['tags'])}]" if m.get('tags') else ""
        print(f"   [{i}] {m['file']}{tags_str} (评分:{m['score']}) {m['modified']}")
    return 0


def _h_load(args):
    C = get_colors()
    result = load_memory(
        args.workspace, mode=args.mode, days=getattr(args, 'days', None),
        limit=getattr(args, 'limit', 10),
        query=getattr(args, 'query', None),
        tags=[t.strip() for t in args.tags.split(",")] if getattr(args, 'tags', None) else None,
        auto_compact=not getattr(args, 'no_compact', False),
    )
    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"\n{C['bright']}\U0001f4da 加载记忆 ({len(result['loaded'])} 个文件){C['reset']}")
    print(f"   预估Token: {result['total_tokens_estimate']}（估算）")
    if result.get('relevance_used'):
        print(f"   \U0001f9e0 已按任务相关性筛选（query/tags）")
    if result.get('compacted'):
        print(f"   \U0001f50d 已触发超预算自动压实，记忆已压至预算内")
    for item in result["loaded"][:10]:
        print(f"   \u2022 {item['file']} ({item['type']}) {item.get('keywords', [])}")
    return 0


def _h_summarize(args):
    result = summarize_memory(args.workspace, progress_callback=_make_progress(_("progress_summarizing")))
    if _emit(args, result):
        return 0
    print(f"\n\U0001f4dd 摘要生成完成: {len(result['summarized'])} 个文件")
    return 0


def _h_report(args):
    res = generate_memory_report(args.workspace)
    if _emit(args, res or {"status": "report_generated"}):
        return 0
    return 0


def _h_cache_reminder(args):
    res = cache_reminder(args.workspace)
    if _emit(args, res or {"status": "ok"}):
        return 0
    return 0


def _h_cache_clean(args):
    res = cache_clean(args.workspace, dry_run=not getattr(args, 'execute', False),
                      confirm=getattr(args, 'execute', False), cache_type='all')
    if _emit(args, res or {"status": "ok"}):
        return 0
    return 0


def _h_clean(args):
    C = get_colors()
    preview = generate_cleanup_preview(args.workspace, dry_run=True)
    if _emit(args, preview):
        return 0
    print_preview(preview)
    if getattr(args, 'execute', False):
        if _require_confirmation(
            f"\n{C['yellow']}\u26a0\ufe0f  将永久删除 {len(preview.get('files_to_clean', []))} 个文件（不可恢复）{''}\n"
            f"{C['yellow']}回复「同意」确认删除:{''}",
            force=getattr(args, 'force', False)
        ):
            exec_result = execute_cleanup(
                args.workspace, confirm=True,
                progress_callback=_make_progress(_("progress_cleaning")))
            print(f"\n{C['green']}\u2705 已删除 {exec_result['deleted_count']} 个文件，释放 {exec_result['deleted_size_kb']:.1f}KB{''}")
            if exec_result.get('deleted_size_kb'):
                print(_("clean_release_line").format(
                    kb=exec_result['deleted_size_kb'],
                    tokens=kb_to_tokens(exec_result['deleted_size_kb'])))
        else:
            print(f"\n{C['yellow']}\u274c 已取消{''}")
    return 0


def _h_archive(args):
    result = archive_old_memory(args.workspace, args.days, confirm=getattr(args, 'execute', False))
    if _emit(args, result):
        return 0
    print(f"\n归档结果: 已归档 {result['archived_count']} 个文件 ({result['archived_size_kb']:.1f}KB)")
    print(f"归档位置: {result['archive_path']}")
    return 0


def _h_auto_clean(args):
    C = get_colors()
    content_filter = getattr(args, 'filter', None)
    confirm_action = getattr(args, 'execute', False)
    result = auto_clean_memory(args.workspace, dry_run=not confirm_action,
                               content_filter=content_filter, confirm_action=confirm_action)
    if _emit(args, result):
        return 0
    print(f"\n{C['bright']}{'='*50}{C['reset']}")
    print(f"{C['cyan']}\U0001f9f9 {_('differential_auto_clean')}{C['reset']}")
    print(f"{'='*50}")
    print(f"\U0001f4ca 推送类(>1天强制清理): {result['clean_summary']['push_to_remind']} 个")
    print(f"\U0001f4ca 个人/工作(>5天提醒): {result['clean_summary']['personal_work_to_remind']} 个")
    print(f"\U0001f4ca 其他(>1天提醒): {result['clean_summary']['other_to_remind']} 个")
    total_remind = sum(result["clean_summary"].values())
    total_kept = len(result["kept_files"])
    if total_remind > 0:
        print(f"\n{C['yellow']}提醒清理 ({total_remind} 个文件):{''}")
        for f in result.get("remind_files", []):
            print(f"   \u2022 {f['name']} ({f['age_days']}天前) [{f['type']}]")
    print(f"\n{C['green']}保留 ({total_kept} 个文件):{''}")
    for f in result.get("kept_files", []):
        print(f"   \u2713 {f['name']} {f.get('reason', '')}")
    return 0


def _h_export(args):
    result = export_memories(args.workspace, args.output,
                             progress_callback=_make_progress(_("progress_exporting")))
    if _emit(args, result):
        return 0
    if "error" in result:
        print(f"\u274c {result['error']}")
    else:
        print(f"\u2705 {result.get('message', '导出完成')} {result['exported_file']} ({result['size_kb']}KB)")
    return 0


def _h_import(args):
    result = import_memories(args.workspace, args.input)
    if _emit(args, result):
        return 0
    print(f"导入完成: {result.get('imported_files', 0)} 个文件, {result.get('imported_summaries', 0)} 个摘要")
    return 0


def _h_config(args):
    C = get_colors()
    config = __import__("memory_manager.config", fromlist=["load_config"]).load_config()
    if hasattr(args, 'key') and args.key and hasattr(args, 'value') and args.value:
        from .config import config_memory
        result = config_memory(args.workspace, key=args.key, value=args.value)
        if _emit(args, result):
            return 0
        print(f"\n配置已更新: {args.key} = {args.value}")
    else:
        if _emit(args, config):
            return 0
        print(f"\n当前配置:")
        for k, v in sorted(config.items()):
            print(f"  {k}: {v}")
    return 0


def _h_token_check(args):
    C = get_colors()
    result = token_check(args.workspace)
    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"\n{result['emoji']} {result['message']}")
    tag = _('token_estimated_tag')
    print(f"   今日消耗: {result['today_tokens']:,} tokens {tag}")
    print(f"   预算: {result['budget']:,} tokens")
    print(f"   使用率: {result['ratio']*100:.1f}%")
    remaining = max(result['budget'] - result['today_tokens'], 0)
    print(f"   剩余预算: {remaining:,} tokens {tag}")
    try:
        trend = token_trends(args.workspace, period="daily", days_back=7)
        avg = trend.get("totals", {}).get("avg_daily_tokens", 0)
        print(f"   近7日日均: {avg:,} tokens {tag}")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("non-fatal: %s", e)
    if result.get('note'):
        print(f"   {result['note']}")
    return 0


def _h_token_trends(args):
    C = get_colors()
    period = getattr(args, 'period', 'week')
    days_back = getattr(args, 'days', None)
    result = token_trends(args.workspace, period=period, days_back=days_back)
    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    period_label = {"daily": "日", "week": "周", "month": "月"}.get(period, period)
    print(f"\n{C['cyan']}\U0001f4ca {_('token_trends_header').format(period=period_label)}{C['reset']}")
    print(f"{'='*50}")
    totals = result.get("totals", {})
    if totals.get("days_with_data", 0) == 0:
        print(f"   {_('token_trends_no_data')}")
    else:
        print(f"   {_('token_trends_total')}: {totals['total_tokens']:,} tokens {_('token_estimated_tag')}")
        print(f"   {_('token_trends_daily_avg')}: {totals['avg_daily_tokens']:,} tokens {_('token_estimated_tag')}")
        print(f"   {_('token_trends_ops')}: {totals['total_operations']:,}")
        print()
        for agg in result.get("aggregated", []):
            label = agg.get("label", "")
            tokens = agg.get("tokens", 0)
            ops = agg.get("operations_count", 0)
            bar_len = min(int(tokens / max(totals['avg_daily_tokens'], 1) * 10), 40)
            bar = "\u2588" * max(bar_len, 1)
            print(f"   {label:>12s} | {bar} {tokens:,} ({ops} ops)")
    print(f"{'='*50}")
    return 0


def _h_scan(args):
    result = scan_workspace(args.workspace)
    if _emit(args, result):
        return 0
    print_report(result)
    return 0


def _h_prompt_list(args):
    C = get_colors()
    result = list_prompts(args.workspace, tag=getattr(args, 'tag', None))
    if _emit(args, result):
        return 0
    if result["total"] == 0:
        print(f"\n{C['yellow']}\U0001f4cb 暂无Prompt模板{C['reset']}")
        print(f"   提示: 使用 prompt-save 保存第一个模板")
    else:
        print(f"\n{C['bright']}\U0001f4cb Prompt模板清单 ({result['total']} 个){C['reset']}")
        print(f"{'='*50}")
        for p in result["prompts"]:
            tags_str = f" [{','.join(p['tags'])}]" if p.get('tags') else ""
            desc = f" - {p['description']}" if p.get('description') else ""
            print(f"   \U0001f4dd {p['name']}{tags_str}{desc}")
            print(f"      版本:{p['version']} | 修改:{p['modified']} | {p['size_kb']:.1f}KB")
    return 0


def _h_prompt_get(args):
    C = get_colors()
    result = get_prompt(args.workspace, args.name)
    if _emit(args, result):
        return 0
    if not result.get("found"):
        print(f"\n{C['red']}\u274c {result.get('error', '未找到模板')}{C['reset']}")
    else:
        print(f"\n{C['bright']}\U0001f4dd {result['name']}{C['reset']}")
        tags_str = f" [{','.join(result['tags'])}]" if result.get('tags') else ""
        print(f"   标签:{tags_str} | 版本:{result['version']}")
        print(f"{'='*50}")
        print(result["content"])
    return 0


def _h_prompt_save(args):
    C = get_colors()
    tags = [t.strip() for t in args.tags.split(",")] if getattr(args, 'tags', None) else None
    result = save_prompt(
        args.workspace, args.name,
        content=args.content,
        tags=tags,
        description=getattr(args, 'description', ''),
        category=getattr(args, 'category', ''),
    )
    if result.get("saved"):
        print(f"\n{C['green']}\u2705 Prompt模板已保存: {result['name']} (v{result['version']}){C['reset']}")
        if result.get('tags'):
            print(f"   标签: [{', '.join(result['tags'])}]")
    else:
        print(f"\n{C['red']}\u274c 保存失败: {result.get('error', '未知错误')}{C['reset']}")
    return 0


def _h_prompt_search(args):
    C = get_colors()
    result = search_prompts(
        args.workspace,
        keyword=getattr(args, 'keyword', None),
        tag=getattr(args, 'tag', None),
    )
    if _emit(args, result):
        return 0
    if result["total"] == 0:
        print(f"\n{C['yellow']}\U0001f50d 未找到匹配的Prompt模板{C['reset']}")
    else:
        print(f"\n{C['bright']}\U0001f50d Prompt搜索结果 ({result['total']} 个){C['reset']}")
        for p in result["prompts"]:
            tags_str = f" [{','.join(p['tags'])}]" if p.get('tags') else ""
            score_str = f" (匹配:{p['score']})" if p.get('score') else ""
            print(f"   \U0001f4dd {p['name']}{tags_str}{score_str}")
    return 0


def _h_self_test(args):
    res = _handle_self_test(args)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0
