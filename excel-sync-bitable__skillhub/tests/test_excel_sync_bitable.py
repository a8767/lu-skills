import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "excel_sync_bitable.py")
SPEC = importlib.util.spec_from_file_location("excel_sync_bitable", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SynchronizerTests(unittest.TestCase):
    def test_frame_records_normalizes_datetime_and_empty_values(self):
        frame = pd.DataFrame({"ID": [1], "When": [pd.Timestamp("2026-07-23 08:30")], "Note": [None]})
        record = MODULE.frame_records(frame)[0]
        self.assertEqual(record["ID"], 1.0)
        self.assertEqual(record["When"], "2026-07-23 08:30:00")
        self.assertIsNone(record["Note"])

    def test_duplicate_source_key_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.ensure_unique_keys([{"ID": "A"}, {"ID": "A"}], "ID", "source")

    def test_remote_duplicate_key_is_rejected(self):
        rows = [{"record_id": "rec1", "fields": {"ID": "A"}}, {"record_id": "rec2", "fields": {"ID": "A"}}]
        with self.assertRaises(ValueError):
            MODULE.remote_key_map(rows, "ID")

    def test_response_parser_finds_records(self):
        response = {"data": {"items": [{"record_id": "rec1", "fields": {"ID": "A"}}]}}
        self.assertEqual(MODULE.records_from_response(response)[0]["record_id"], "rec1")

    def test_response_parser_supports_current_matrix_format(self):
        response = {"data": {"fields": ["ID", "Text"], "data": [["A", "hello"]], "record_id_list": ["rec1"]}}
        record = MODULE.records_from_response(response)[0]
        self.assertEqual(record["record_id"], "rec1")
        self.assertEqual(record["fields"], {"ID": "A", "Text": "hello"})

    def test_field_parser_supports_current_fields_format(self):
        response = {"data": {"fields": [{"id": "fld1", "name": "ID", "type": "text"}]}}
        self.assertEqual(MODULE.field_items(response)[0]["name"], "ID")

    def test_chunk_respects_limit(self):
        self.assertEqual(list(MODULE.chunk([1, 2, 3], 2)), [[1, 2], [3]])

    def test_numeric_key_tokens_match_excel_and_api_values(self):
        self.assertEqual(MODULE.key_token(1001.0), MODULE.key_token(1001))

    def test_datetime_schema_type_uses_current_cli_name(self):
        self.assertEqual(MODULE.infer_field_type(pd.Series(pd.to_datetime(["2026-07-23"]))), "datetime")

    def test_string_boolean_is_inferred_and_adapted(self):
        series = pd.Series(["yes", "no"])
        self.assertEqual(MODULE.infer_field_type(series), "checkbox")
        self.assertTrue(MODULE.adapt_value("yes", "checkbox", "Done", 2))
        self.assertFalse(MODULE.adapt_value("no", "checkbox", "Done", 3))

    def test_existing_number_field_adapts_string_value(self):
        self.assertEqual(MODULE.adapt_value("1,234.5", "number", "Amount", 2), 1234.5)

    def test_lark_cli_executable_honors_override(self):
        old_value = os.environ.get("LARK_CLI_BIN")
        os.environ["LARK_CLI_BIN"] = "custom-lark-cli"
        try:
            self.assertEqual(MODULE.lark_cli_executable(), "custom-lark-cli")
        finally:
            if old_value is None:
                del os.environ["LARK_CLI_BIN"]
            else:
                os.environ["LARK_CLI_BIN"] = old_value

    @patch.object(MODULE.os, "name", "nt")
    @patch.object(MODULE.os.path, "isfile", return_value=True)
    @patch.object(MODULE.shutil, "which", side_effect=["C:/node.exe"])
    @patch.object(MODULE, "lark_cli_executable", return_value="C:/npm/lark-cli.cmd")
    def test_windows_command_uses_node_runner(self, _, __, ___):
        command = MODULE.lark_cli_command(["base", "+url-resolve"])
        self.assertEqual(command[0], "C:/node.exe")
        self.assertEqual(os.path.normpath(command[1]), os.path.normpath("C:/npm/node_modules/@larksuite/cli/scripts/run.js"))

    def test_create_preview_runs_end_to_end_without_a_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "orders.csv")
            with open(source, "w", encoding="utf-8", newline="") as handle:
                handle.write("OrderId,Amount\n1001,12.5\n1002,15\n")
            result = subprocess.run(
                [sys.executable, SCRIPT, "create", "--input", source, "--app-name", "Test", "--table-name", "Orders"],
                capture_output=True, text=True
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Create preview: Base=Test, table=Orders, fields=2, rows=2", result.stdout)
        self.assertIn("Preview only", result.stdout)


if __name__ == "__main__":
    unittest.main()
