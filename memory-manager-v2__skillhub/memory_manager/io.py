import logging
logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
"""
记忆管家 V3.0 - 导入导出备份恢复
来源: memory_manager.py (export/import/backup/restore)
V3.0: 模块化重构
"""

import json
import shutil
import gzip
from datetime import datetime
from pathlib import Path

from .config import (
    VERSION, _, get_colors,
    MAX_FILE_SIZE,
    load_config,
    is_symlink, get_file_info,
)
from .token import compute_content_hash

# ZIP 安全限制常量
MAX_IMPORT_SINGLE_FILE_SIZE = MAX_FILE_SIZE          # 单文件 1MB 上限
MAX_IMPORT_TOTAL_SIZE = 50 * 1024 * 1024             # 解压总大小 50MB 上限
MAX_IMPORT_ENTRIES = 1000                             # ZIP 条目数上限


def _export_invoke_progress(progress_callback, done, total, name):
    """安全调用进度回调（忽略非致命异常）。"""
    if progress_callback is None:
        return
    try:
        progress_callback(done, total, name)
    except Exception as e:
        logger.warning("non-fatal: %s", e)


def _export_summary_entries(zf, summary_dir):
    """将 .summary 目录下的摘要文件追加进导出 ZIP。"""
    if not summary_dir.exists():
        return
    for sum_file in summary_dir.glob("*.summary"):
        if is_symlink(sum_file):
            continue
        safe_name = (".summary/" + sum_file.name)
        zf.write(sum_file, arcname=safe_name)


def export_memories(workspace_path, output_file, progress_callback=None):
    workspace = Path(workspace_path).resolve()
    memory_dir = workspace / ".workbuddy" / "memory"
    output_path = Path(output_file)

    if not memory_dir.exists():
        return {"error": _("memory_dir_not_exist_detail")}

    error_note = _("export_failed") if _("export_failed") != "export_failed" else "Export failed"

    try:
        import zipfile

        md_files = [f for f in memory_dir.glob("*.md") if not is_symlink(f)]
        total = len(md_files)
        done = 0
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for md_file in md_files:
                safe_name = md_file.relative_to(memory_dir).as_posix()
                zf.write(md_file, arcname=safe_name)
                done += 1
                _export_invoke_progress(progress_callback, done, total, md_file.name)

            _export_summary_entries(zf, workspace / ".workbuddy" / ".summary")

        file_size = output_path.stat().st_size
        return {
            "exported_file": str(output_path),
            "size_kb": round(file_size / 1024, 2),
            "message": _("export_success")
        }
    except ImportError:
        return {"error": error_note}


def _import_validate_zip(zf, result):
    """ZIP Bomb 预检：单文件上限记入 errors（不中断），总条目/总大小超限返回 hard error。
    返回 (total_uncompressed, hard_error)。"""
    total_uncompressed = 0
    entry_count = 0
    for member in zf.infolist():
        entry_count += 1
        total_uncompressed += member.file_size
        if member.file_size > MAX_IMPORT_SINGLE_FILE_SIZE:
            result["errors"].append(
                f"安全拒绝: {member.filename} (解压后 {member.file_size // 1024}KB 超过单文件上限)")
    if entry_count > MAX_IMPORT_ENTRIES:
        return total_uncompressed, f"安全拒绝: ZIP 包含 {entry_count} 个条目，超过 {MAX_IMPORT_ENTRIES} 上限"
    if total_uncompressed > MAX_IMPORT_TOTAL_SIZE:
        return total_uncompressed, (f"安全拒绝: 解压总大小 {total_uncompressed // (1024*1024)}MB 超过 "
                                    f"{MAX_IMPORT_TOTAL_SIZE // (1024*1024)}MB 上限")
    return total_uncompressed, None


def _path_has_traversal(raw_name):
    """检测 ZIP 条目是否含路径穿越分量。"""
    parts = raw_name.replace('\\', '/').split('/')
    return any(p in ('..', '') and i > 0 for i, p in enumerate(parts))


def _path_is_absolute(raw_name):
    """检测 ZIP 条目是否为绝对路径（含盘符）。"""
    return (raw_name.startswith('/') or raw_name.startswith('\\')
            or (len(raw_name) >= 2 and raw_name[1] == ':'))


def _import_safe_target(raw_name, workspace, memory_dir, summary_dir):
    """ZIP Slip 五层防御：返回 (target_path, is_summary, error)。
    error 非空=拒绝该条目；target_path 为 None 且 error 为空=空路径跳过。"""
    if _path_has_traversal(raw_name):
        return None, False, f"安全拒绝: {raw_name} (包含路径穿越分量)"
    if _path_is_absolute(raw_name):
        return None, False, f"安全拒绝: {raw_name} (绝对路径)"
    safe_path = raw_name.replace('\\', '/').lstrip('/')
    if not safe_path or safe_path in ('.', '..'):
        return None, False, None  # 空路径：静默跳过
    if not (safe_path.endswith('.md') or safe_path.endswith('.summary')):
        return None, False, f"安全拒绝: {safe_path} (不允许的文件类型)"

    is_summary = safe_path.startswith('.summary/')
    target_dir = summary_dir if is_summary else memory_dir
    target_name = safe_path[len('.summary/'):] if is_summary else safe_path
    target_path = target_dir / target_name

    # 5) 最终边界校验：解析后必须落在工作空间内（防御符号链接逃逸）
    try:
        resolved = target_path.resolve()
        resolved.relative_to(workspace)
    except (ValueError, OSError):
        return None, False, f"安全拒绝: {safe_path} (路径超出工作空间)"

    return resolved, is_summary, None


def _safe_unlink(target_path):
    """安全删除（忽略非致命错误）。"""
    try:
        target_path.unlink()
    except OSError as e:
        logger.warning("non-fatal: %s", e)


def _copy_zip_member_chunks(source, target_path, result, counter, dest):
    """分块复制 ZIP 成员，追踪总字节，超限返回 'exceed'。"""
    while True:
        chunk = source.read(64 * 1024)
        if not chunk:
            return "ok"
        counter[0] += len(chunk)
        if counter[0] > MAX_IMPORT_TOTAL_SIZE:
            _safe_unlink(target_path)
            result["errors"].append(
                f"安全拒绝: 解压总大小超过 {MAX_IMPORT_TOTAL_SIZE // (1024*1024)}MB 限制，导入中断")
            return "exceed"
        dest.write(chunk)


def _import_write_member(zf, member, target_path, is_summary, result, counter):
    """安全写入单条 ZIP 成员（分块 + ZIP Bomb 总字节追踪）。
    counter=[extracted_total] 跨成员累计；返回 'exceed' 表示中断整个导入。"""
    try:
        with zf.open(member) as source:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'wb') as dest:
                status = _copy_zip_member_chunks(source, target_path, result, counter, dest)
        if status == "exceed":
            return "exceed"
        if is_summary:
            result["imported_summaries"] += 1
        else:
            result["imported_files"] += 1
        return "ok"
    except Exception as e:
        result["errors"].append(f"{target_path.name}: {str(e)}")
        return "error"


def import_memories(workspace_path, input_file):
    workspace = Path(workspace_path).resolve()
    memory_dir = workspace / ".workbuddy" / "memory"
    summary_dir = workspace / ".workbuddy" / ".summary"
    input_path = Path(input_file)

    if not input_path.exists():
        return {"error": _("import_file_not_exist")}

    error_note = _("import_failed") if _("import_failed") != "import_failed" else "Import failed"

    memory_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    try:
        import zipfile

        result = {"imported_files": 0, "imported_summaries": 0, "errors": []}

        with zipfile.ZipFile(input_path, 'r') as zf:
            # ---- ZIP Bomb 防御：预检 ----
            _uncompressed, precheck_err = _import_validate_zip(zf, result)
            if precheck_err:
                return {**result, "error": precheck_err}

            counter = [0]  # 实际写入字节数追踪（ZIP Bomb 防御，跨成员累计）

            for member in zf.infolist():
                target_path, is_summary, error = _import_safe_target(
                    member.filename, workspace, memory_dir, summary_dir)
                if error:
                    result["errors"].append(error)
                    continue
                if target_path is None:
                    continue

                status = _import_write_member(zf, member, target_path, is_summary, result, counter)
                if status == "exceed":
                    return result

        return result
    except ImportError:
        return {"error": error_note}


def _backup_load_manifest(manifest_file):
    """读取上次备份清单（不存在/损坏返回空）。"""
    if not manifest_file.exists():
        return {}
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8")).get("files", {})
    except (json.JSONDecodeError, IOError, KeyError) as e:
        logger.warning("non-fatal: %s", e)
        return {}


def _backup_one_file(md_file, backup_path, memory_path, last_backup, incremental, dry_run, result):
    """备份单文件：dry_run 只计数，否则拷贝并计数。"""
    mtime, size_kb = get_file_info(md_file)
    if mtime is None:
        return
    rel = md_file.relative_to(memory_path)
    file_key = str(rel)
    current_hash = compute_content_hash(md_file)
    if incremental and file_key in last_backup and last_backup[file_key].get("hash") == current_hash:
        return
    is_new = file_key not in last_backup
    key = "files_copied" if is_new else "files_updated"
    if dry_run:
        result[key] += 1
        result["total_size_kb"] += size_kb
        return
    try:
        (backup_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md_file, backup_path / rel)
        result[key] += 1
        result["total_size_kb"] += size_kb
    except (OSError, IOError, PermissionError) as e:
        logger.warning("non-fatal: %s", e)


def _backup_write_manifest(backup_path, memory_path):
    """写入备份清单（含哈希与体积）。"""
    manifest = {
        "last_backup": datetime.now().isoformat(),
        "files": {
            str(f.relative_to(memory_path)): {
                "hash": compute_content_hash(f),
                "size_kb": get_file_info(f)[1],
            }
            for f in memory_path.glob("*.md")
        },
    }
    (backup_path / ".backup_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def backup_memory(workspace_path, backup_path=None, dry_run=True, incremental=True):
    config = load_config()
    bp_cfg = config.get("_backup_config", {})
    if backup_path is None:
        backup_path = bp_cfg.get("local_path", "")
    if not backup_path:
        return {"error": _("backup_config_missing")}
    backup_path = Path(backup_path).resolve()
    base_path = Path(workspace_path).resolve()
    memory_path = base_path / ".workbuddy" / "memory"
    result = {"backup_path": str(backup_path), "files_copied": 0, "files_updated": 0, "total_size_kb": 0}
    if not memory_path.exists():
        result["error"] = _("memory_dir_not_exist")
        return result
    if not dry_run:
        backup_path.mkdir(parents=True, exist_ok=True)

    manifest_file = backup_path / ".backup_manifest.json"
    last_backup = _backup_load_manifest(manifest_file)

    for md_file in memory_path.glob("*.md"):
        if is_symlink(md_file):
            continue
        _backup_one_file(md_file, backup_path, memory_path, last_backup, incremental, dry_run, result)

    if not dry_run:
        _backup_write_manifest(backup_path, memory_path)
    return result


def restore_backup(workspace_path, backup_path=None, dry_run=True):
    config = load_config()
    bp_cfg = config.get("_backup_config", {})
    if backup_path is None:
        backup_path = bp_cfg.get("local_path", "")
    if not backup_path:
        return {"error": _("backup_config_missing")}
    backup_path = Path(backup_path).resolve()
    manifest_file = backup_path / ".backup_manifest.json"
    if not manifest_file.exists():
        return {"error": _("backup_record_not_exist")}
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"error": _("backup_record_corrupted")}
    result = {"files_restored": 0}
    for file_key in manifest.get("files", {}):
        src = backup_path / file_key
        dst = Path(workspace_path).resolve() / ".workbuddy" / "memory" / file_key
        if src.exists():
            if dry_run:
                result["files_restored"] += 1
            else:
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    result["files_restored"] += 1
                except (OSError, IOError, PermissionError) as e:
                    logger.warning("non-fatal: %s", e)

    return result
