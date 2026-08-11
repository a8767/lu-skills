#!/usr/bin/env python3
"""Unit tests for the Windows Playwright collection entry points."""

from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


workflow = load_module("collect_playwright_workflow", "collect_playwright.py")
collector = load_module("playwright_browser_collector", "playwright_collect.py")


class WorkflowTests(unittest.TestCase):
    def test_windows_profile_uses_local_app_data(self) -> None:
        actual = workflow.default_profile_dir(
            platform_name="win32",
            env={"LOCALAPPDATA": "D:/LocalData"},
            home=Path("test-home"),
        )
        self.assertEqual(
            actual,
            Path("D:/LocalData/PersonalAIWorkbench/douyin-playwright-profile"),
        )

    def test_explicit_profile_override_wins(self) -> None:
        actual = workflow.default_profile_dir(
            platform_name="win32",
            env={"PERSONAL_WORKBENCH_DOUYIN_PROFILE": "E:/browser-profile"},
            home=Path("test-home"),
        )
        self.assertEqual(actual, Path("E:/browser-profile"))

    def test_validate_work_ids_deduplicates(self) -> None:
        self.assertEqual(workflow.validate_work_ids("123, 456,123"), ["123", "456"])
        with self.assertRaises(workflow.WorkflowError):
            workflow.validate_work_ids("123,not-an-id")

    def test_previous_work_ids_reads_only_numeric_ids(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            target = Path(value) / "works.csv"
            with target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["平台作品ID", "标题"])
                writer.writeheader()
                writer.writerow({"平台作品ID": "1001", "标题": "demo"})
                writer.writerow({"平台作品ID": "invalid", "标题": "demo"})
                writer.writerow({"平台作品ID": "1001", "标题": "demo"})
            self.assertEqual(workflow.previous_work_ids(target), ["1001"])

    def test_atomic_replace_directory_replaces_and_removes_backup(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            stage = root / "stage"
            target = root / "target"
            backup = root / "backup"
            stage.mkdir()
            target.mkdir()
            (stage / "current.json").write_text("new", encoding="utf-8")
            (target / "current.json").write_text("old", encoding="utf-8")

            workflow.atomic_replace_directory(stage, target, backup)

            self.assertEqual((target / "current.json").read_text(encoding="utf-8"), "new")
            self.assertFalse(stage.exists())
            self.assertFalse(backup.exists())

    def test_kept_backup_can_restore_previous_data(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            stage = root / "stage"
            target = root / "target"
            backup = root / "backup"
            stage.mkdir()
            target.mkdir()
            (stage / "current.json").write_text("invalid-new", encoding="utf-8")
            (target / "current.json").write_text("valid-old", encoding="utf-8")

            workflow.atomic_replace_directory(stage, target, backup, keep_backup=True)
            workflow.rollback_directory_swap(target, backup)

            self.assertEqual(
                (target / "current.json").read_text(encoding="utf-8"), "valid-old"
            )
            self.assertFalse(backup.exists())


class CollectorUtilityTests(unittest.TestCase):
    def test_safe_filename_removes_windows_reserved_characters(self) -> None:
        self.assertEqual(collector.safe_filename('a:b/c*?"d.xlsx'), "a_b_c___d.xlsx")

    def test_unique_path_adds_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "export.xlsx").touch()
            self.assertEqual(collector.unique_path(root, "export.xlsx").name, "export-2.xlsx")

    def test_parse_work_ids_rejects_non_numeric_values(self) -> None:
        self.assertEqual(collector.parse_work_ids("11,22,11"), ["11", "22"])
        with self.assertRaises(Exception):
            collector.parse_work_ids("11,bad")

    def test_repository_path_detection(self) -> None:
        self.assertTrue(collector.is_within(collector.SCRIPT_DIR, collector.REPO_ROOT))
        with tempfile.TemporaryDirectory() as value:
            self.assertFalse(collector.is_within(Path(value), collector.REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
