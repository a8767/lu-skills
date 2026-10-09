#!/usr/bin/env python3

import importlib.util
import sys
import unittest
from datetime import timedelta
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze_snapshot.py")
SPEC = importlib.util.spec_from_file_location("analyze_snapshot", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DouyinFeedbackTests(unittest.TestCase):
    def test_stable_collection_is_fixed_to_ego_lite(self):
        scripts = [
            MODULE_PATH.with_name("collect.sh"),
            MODULE_PATH.with_name("ego_collect.sh"),
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in scripts)
        self.assertNotIn("DOUYIN_BROWSER_ENGINE", source)
        self.assertNotIn("npm run probe", source)
        self.assertIn("ego_collect.sh", source)

    def test_parse_number(self):
        self.assertEqual(MODULE.parse_number("14.07%"), 0.1407)
        self.assertEqual(MODULE.parse_number("1.43万"), 14300)
        self.assertIsNone(MODULE.parse_number("-"))

    def test_normalize_title_ignores_hashtags_and_punctuation(self):
        value = "外部资料如何可靠转成Markdown？ #个人知识库 #AI"
        self.assertEqual(MODULE.normalize_title(value), "外部资料如何可靠转成markdown")

    def test_content_line_uses_title_not_hashtag(self):
        config = {
            "content_lines": [
                {"name": "知识管理", "title_keywords": ["知识库"]},
                {"name": "学习方法", "title_keywords": ["学习"]},
            ],
            "default_content_line": "未分类",
        }
        row = {"title": "AI快速学习法"}
        self.assertEqual(MODULE.classify_content_line(row, config), "学习方法")

    def test_quality_detects_duplicate(self):
        row = {
            "title": "A",
            "title_key": "a",
            "published_at": MODULE.datetime(2026, 7, 25),
            "status": "公开",
            **{field: 1 for field in MODULE.COUNT_FIELDS},
            **{field: 0.5 for field in MODULE.RATE_FIELDS},
        }
        result = MODULE.validate_rows(
            [row, row.copy()],
            MODULE.REQUIRED_COLUMNS,
            None,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["duplicate_count"], 1)

    def test_immature_work_is_data_only_and_low_confidence(self):
        config = {
            "minimum_comparison_plays": 1000,
            "minimum_comparison_age_hours": 24,
        }
        focus = {
            "title": "新作品",
            "title_key": "新作品",
            "published_at": MODULE.datetime.now() - timedelta(hours=2),
            "format": "1-3min视频",
            "content_line": "知识管理",
            "plays": 572,
            "two_second_bounce_rate": 0.54,
            "five_second_rate": 0.18,
            "completion_rate": 0.006,
            "value_action_rate": 0.008,
            "profile_visit_rate": 0.0,
            "follow_rate": 0.0,
        }
        peers = [
            {
                **focus,
                "title": f"历史{i}",
                "title_key": f"历史{i}",
                "published_at": MODULE.datetime(2026, 7, i + 1),
                "plays": 2000,
                "two_second_bounce_rate": 0.41,
                "five_second_rate": 0.28,
                "completion_rate": 0.024,
                "value_action_rate": 0.013,
                "profile_visit_rate": 0.01,
                "follow_rate": 0.002,
            }
            for i in range(5)
        ]
        result = MODULE.diagnose_latest(
            [focus, *peers],
            MODULE.datetime.now(),
            config,
            None,
        )
        self.assertFalse(result["mature_for_comparison"])
        self.assertEqual(result["confidence"], "low")
        self.assertNotIn("decision", result)
        self.assertNotIn("monitor", result)


if __name__ == "__main__":
    unittest.main()
