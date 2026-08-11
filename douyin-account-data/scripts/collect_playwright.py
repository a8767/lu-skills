#!/usr/bin/env python3
"""Cross-platform Playwright entry point for Douyin Creator Center collection."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PLAYWRIGHT_COLLECTOR = SCRIPT_DIR / "playwright_collect.py"
INVENTORY_SCRIPT = SCRIPT_DIR / "inventory_exports.py"
ANALYSIS_SCRIPT = SCRIPT_DIR / "analyze_snapshot.py"
PUBLISH_SCRIPT = SCRIPT_DIR / "publish_workbench_data.mjs"


class WorkflowError(RuntimeError):
    def __init__(self, status: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect authorized Douyin Creator Center exports with Playwright."
    )
    parser.add_argument("--dashboard-root", type=Path)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--work-ids", default="")
    parser.add_argument(
        "--browser-channel",
        choices=("chromium", "chrome", "msedge"),
        default=os.environ.get("PERSONAL_WORKBENCH_PLAYWRIGHT_CHANNEL", "chromium"),
    )
    parser.add_argument("--profile-dir", type=Path)
    parser.add_argument("--login-timeout", type=int, default=300)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate Python, Node.js, Playwright, and the selected browser without collecting data.",
    )
    return parser.parse_args(argv)


def default_profile_dir(
    platform_name: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    platform_name = platform_name or sys.platform
    env = os.environ if env is None else env
    configured = env.get("PERSONAL_WORKBENCH_DOUYIN_PROFILE")
    if configured:
        return Path(configured).expanduser()

    home = Path.home() if home is None else home
    if platform_name.startswith("win"):
        base = Path(env.get("LOCALAPPDATA") or home / "AppData" / "Local")
        return base / "PersonalAIWorkbench" / "douyin-playwright-profile"
    if platform_name == "darwin":
        return home / "Library" / "Application Support" / "PersonalAIWorkbench" / "douyin-playwright-profile"
    base = Path(env.get("XDG_STATE_HOME") or home / ".local" / "state")
    return base / "personal-ai-workbench" / "douyin-playwright-profile"


def validate_work_ids(value: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    if any(not item.isdigit() for item in values):
        raise WorkflowError("invalid_input", "--work-ids must contain comma-separated numeric IDs", 65)
    return list(dict.fromkeys(values))


def previous_work_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        values = [str(row.get("平台作品ID", "")).strip() for row in rows]
    return list(dict.fromkeys(value for value in values if value.isdigit()))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def require_runtime(profile_dir: Path) -> str:
    node = shutil.which("node")
    if not node:
        raise WorkflowError("missing_dependency", "Node.js is required", 69)
    if importlib.util.find_spec("openpyxl") is None:
        raise WorkflowError("missing_dependency", "Python package openpyxl is required", 69)
    if importlib.util.find_spec("playwright") is None:
        raise WorkflowError(
            "missing_dependency",
            "Python package playwright is required; install requirements-windows.txt first",
            69,
        )
    if is_within(profile_dir, REPO_ROOT):
        raise WorkflowError(
            "invalid_profile",
            "Playwright profile must be outside the public Skill repository",
            65,
        )
    return node


def run_checked(command: Sequence[str], *, cwd: Path | None = None) -> None:
    subprocess.run(list(command), cwd=cwd, check=True)


def record_failure(
    node: str,
    vault_root: Path,
    store_root: Path,
    status: str,
    message: str,
) -> None:
    if not store_root.is_dir():
        return
    subprocess.run(
        [
            node,
            str(PUBLISH_SCRIPT),
            "--vault",
            str(vault_root),
            "--output",
            str(store_root),
            "--failure-status",
            status,
            "--failure-message",
            message,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def atomic_replace_directory(
    stage: Path, target: Path, backup: Path, *, keep_backup: bool = False
) -> None:
    if backup.exists():
        raise FileExistsError(f"Refusing existing backup path: {backup}")
    moved_existing = False
    if target.exists():
        target.replace(backup)
        moved_existing = True
    try:
        stage.replace(target)
    except Exception:
        if moved_existing and backup.exists() and not target.exists():
            backup.replace(target)
        raise
    if backup.exists() and not keep_backup:
        shutil.rmtree(backup)


def rollback_directory_swap(target: Path, backup: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if backup.exists():
        backup.replace(target)


def browser_command(
    mode: str,
    profile_dir: Path,
    browser_channel: str,
    login_timeout: int,
    output_dir: Path | None = None,
    snapshot_dir: Path | None = None,
    work_ids: Sequence[str] = (),
) -> list[str]:
    command = [
        sys.executable,
        str(PLAYWRIGHT_COLLECTOR),
        mode,
        "--profile-dir",
        str(profile_dir),
        "--browser-channel",
        browser_channel,
        "--login-timeout",
        str(login_timeout),
    ]
    if output_dir is not None:
        command.extend(("--output-dir", str(output_dir)))
    if snapshot_dir is not None:
        command.extend(("--snapshot-dir", str(snapshot_dir)))
    if work_ids:
        command.extend(("--work-ids", ",".join(work_ids)))
    return command


def collect(args: argparse.Namespace) -> dict[str, object]:
    profile_dir = (args.profile_dir or default_profile_dir()).expanduser().resolve()
    node = require_runtime(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    if args.check:
        run_checked(browser_command("check", profile_dir, args.browser_channel, args.login_timeout))
        return {"status": "ready", "browserEngine": "playwright", "channel": args.browser_channel}

    if not args.dashboard_root or not args.vault_root:
        raise WorkflowError(
            "invalid_input",
            "--dashboard-root and --vault-root are required unless --check is used",
            64,
        )

    dashboard_root = args.dashboard_root.expanduser().resolve()
    vault_root = args.vault_root.expanduser().resolve()
    workbench_root = dashboard_root / "Workbench"
    parser_path = workbench_root / "server" / "vault-index.mjs"
    if not parser_path.is_file():
        raise WorkflowError("invalid_dashboard", f"Workbench parser not found: {parser_path}", 66)
    if not vault_root.is_dir():
        raise WorkflowError("invalid_vault", f"Vault root does not exist: {vault_root}", 66)
    if is_within(profile_dir, vault_root) or is_within(profile_dir, dashboard_root):
        raise WorkflowError(
            "invalid_profile",
            "Playwright profile must be outside the dashboard and private Vault",
            65,
        )

    store_parent = vault_root / "30_self_media"
    store_root = store_parent / "douyin"
    work_ids = validate_work_ids(args.work_ids)
    if not work_ids:
        work_ids = previous_work_ids(store_root / "works.csv")

    cycle_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stage: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="personal-workbench-douyin-") as temp_value:
            temp_root = Path(temp_value)
            snapshot_root = temp_root / f"{cycle_stamp}-creator-collector"
            exports_dir = snapshot_root / "00_exports"
            snapshots_dir = snapshot_root / "01_page_snapshots"
            inventory_dir = snapshot_root / "02_inventory"
            analysis_dir = temp_root / "analysis"
            exports_dir.mkdir(parents=True)
            snapshots_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)

            result = subprocess.run(
                browser_command(
                    "collect-weekly",
                    profile_dir,
                    args.browser_channel,
                    args.login_timeout,
                    exports_dir,
                    snapshots_dir,
                    work_ids,
                ),
                check=False,
            )
            if result.returncode == 21:
                raise WorkflowError(
                    "blocked_auth",
                    "Playwright login did not complete; sign in in the opened browser and retry",
                    21,
                )
            if result.returncode != 0:
                raise WorkflowError(
                    "collection_failed",
                    "Playwright Creator Center collection did not complete",
                    22,
                )

            manifest_path = exports_dir / "run_manifest.json"
            if not manifest_path.is_file():
                raise WorkflowError("collection_failed", "Collector manifest is missing", 22)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("result") != "complete":
                raise WorkflowError("collection_failed", "Collector manifest is not complete", 22)
            if not any(exports_dir.glob("*.xlsx")):
                raise WorkflowError("collection_failed", "No official Excel exports were downloaded", 22)

            run_checked(
                [
                    sys.executable,
                    str(INVENTORY_SCRIPT),
                    "--input",
                    str(exports_dir),
                    "--output",
                    str(inventory_dir),
                ]
            )

            analysis_command = [
                sys.executable,
                str(ANALYSIS_SCRIPT),
                "--vault-root",
                str(vault_root),
                "--config",
                str(SKILL_DIR / "assets" / "config.example.json"),
                "--snapshot",
                str(snapshot_root),
                "--output",
                str(analysis_dir),
                "--no-workflow-writeback",
                "--no-latest-pointer",
                "--published-source-root",
                "30_self_media/douyin",
                "--published-work-list",
                "30_self_media/douyin/works.csv",
                "--published-previous",
                "30_self_media/douyin/work-history.csv",
            ]
            previous = store_root / "works.csv"
            if previous.is_file():
                analysis_command.extend(("--previous", str(previous)))
            run_checked(analysis_command)

            analysis_path = analysis_dir / "analysis.json"
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            if analysis.get("data_quality", {}).get("status") in (None, "", "failed"):
                raise WorkflowError("data_quality_failed", "Douyin data quality gate failed", 23)

            store_parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".douyin-staging.", dir=store_parent))
            publish_command = [
                node,
                str(PUBLISH_SCRIPT),
                "--vault",
                str(vault_root),
                "--workbench-root",
                str(workbench_root),
                "--snapshot",
                str(snapshot_root),
                "--analysis",
                str(analysis_path),
                "--output",
                str(stage),
            ]
            existing = store_root / "current.json"
            if existing.is_file():
                publish_command.extend(("--existing", str(existing)))
            run_checked(publish_command)

            backup = store_parent / f".douyin-backup-{cycle_stamp}-{os.getpid()}"
            atomic_replace_directory(stage, store_root, backup, keep_backup=True)
            stage = None
            try:
                run_checked(
                    [
                        node,
                        str(PUBLISH_SCRIPT),
                        "--vault",
                        str(vault_root),
                        "--workbench-root",
                        str(workbench_root),
                        "--output",
                        str(store_root),
                        "--verify",
                    ]
                )
            except Exception:
                rollback_directory_swap(store_root, backup)
                raise
            if backup.exists():
                shutil.rmtree(backup)

            current_path = store_root / "current.json"
            current = json.loads(current_path.read_text(encoding="utf-8"))
            analytics = current.get("douyin", {}).get("analytics", {})
            return {
                "status": "complete",
                "current": str(current_path),
                "capturedAt": current.get("capturedAt"),
                "quality": current.get("dataQuality", {}).get("status"),
                "works": len(current.get("douyin", {}).get("works", [])),
                "deepWorkDetails": len(analytics.get("workDetails", {})),
                "accountDailyRows": len(analytics.get("account", {}).get("daily", [])),
                "collections": len(analytics.get("collections", [])),
                "browserEngine": "playwright",
                "temporarySourcesDeleted": True,
            }
    except WorkflowError as error:
        record_failure(node, vault_root, store_root, error.status, str(error))
        raise
    except subprocess.CalledProcessError as error:
        record_failure(
            node,
            vault_root,
            store_root,
            "workflow_failed",
            f"Workflow command failed with exit code {error.returncode}",
        )
        raise
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = collect(args)
    except WorkflowError as error:
        print(f"status={error.status}", file=sys.stderr)
        print(f"message={error}", file=sys.stderr)
        return error.exit_code
    except subprocess.CalledProcessError as error:
        print("status=workflow_failed", file=sys.stderr)
        print(f"message=Command failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode or 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
