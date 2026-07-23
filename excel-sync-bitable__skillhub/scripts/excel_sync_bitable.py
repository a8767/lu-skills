#!/usr/bin/env python3
"""Safe Excel/CSV <-> Feishu Base synchronizer for lark-cli 1.x."""
from __future__ import print_function

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
try:
    from urllib.parse import parse_qs, urlparse
except ImportError:  # Python 2 compatibility is harmless for old embedded runtimes.
    from urlparse import parse_qs, urlparse

import pandas as pd


WRITABLE_TYPES = set(["text", "number", "date", "datetime", "checkbox", "bool"])


class MissingFieldsConfirmation(Exception):
    """Signal a safe, user-actionable preflight result instead of a write."""


def lark_cli_executable():
    configured = os.environ.get("LARK_CLI_BIN")
    if configured:
        return configured
    if os.name == "nt":
        command = shutil.which("lark-cli.cmd")
        if command:
            return command
    return shutil.which("lark-cli") or "lark-cli"


def lark_cli_command(args):
    """Avoid cmd.exe reparsing URL query strings and JSON on Windows."""
    executable = lark_cli_executable()
    if os.name == "nt" and executable.lower().endswith(".cmd"):
        runner = os.path.join(os.path.dirname(executable), "node_modules", "@larksuite", "cli", "scripts", "run.js")
        node = shutil.which("node")
        if node and os.path.isfile(runner):
            return [node, runner] + args
    return [executable] + args


def cli_json(args):
    """Run lark-cli and return its JSON response, with actionable failures."""
    command = lark_cli_command(args + ["--as", "user", "--format", "json"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("lark-cli failed: {0}".format(result.stderr.strip() or result.stdout.strip()))
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise RuntimeError("lark-cli did not return JSON: {0}".format(result.stdout[:500]))


def walk_values(value, key):
    if isinstance(value, dict):
        if key in value and value[key]:
            yield value[key]
        for item in value.values():
            for found in walk_values(item, key):
                yield found
    elif isinstance(value, list):
        for item in value:
            for found in walk_values(item, key):
                yield found


def first_value(value, *keys):
    for key in keys:
        found = list(walk_values(value, key))
        if found:
            return found[0]
    return None


def read_frame(path):
    if not os.path.isfile(path):
        raise FileNotFoundError("input file not found: {0}".format(path))
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix in (".xlsx", ".xlsm", ".xls"):
        frame = pd.read_excel(path)
    else:
        raise ValueError("only .csv, .xlsx, .xlsm and .xls are supported")
    if frame.empty:
        raise ValueError("input file has no data rows")
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(set(frame.columns)) != len(frame.columns) or any(not column for column in frame.columns):
        raise ValueError("column names must be non-empty and unique")
    return frame


def normalize_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return str(value)


def frame_records(frame):
    return [{column: normalize_value(row[column]) for column in frame.columns} for _, row in frame.iterrows()]


def ensure_unique_keys(records, key, label):
    values = []
    for index, record in enumerate(records, 1):
        value = record.get(key)
        if value is None or str(value).strip() == "":
            raise ValueError("{0} row {1} has a blank key: {2}".format(label, index, key))
        values.append(key_token(value))
    duplicates = sorted(set(value for value in values if values.count(value) > 1))
    if duplicates:
        raise ValueError("{0} has duplicate keys: {1}".format(label, ", ".join(duplicates[:10])))


def key_token(value):
    """Preserve matching semantics for Excel's integer-like numeric keys."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def resolve_base(url):
    response = cli_json(["base", "+url-resolve", "--url", url])
    base_token = first_value(response, "base_token")
    table_id = first_value(response, "table_id")
    if not table_id:
        table_id = parse_qs(urlparse(url).query).get("table", [None])[0]
    if not base_token:
        raise RuntimeError("could not resolve base_token from the supplied URL")
    return base_token, table_id


def records_from_response(response):
    data = response.get("data", {}) if isinstance(response, dict) else {}
    matrix = data.get("data")
    fields = data.get("fields")
    record_ids = data.get("record_id_list")
    if isinstance(matrix, list) and isinstance(fields, list) and isinstance(record_ids, list):
        if not (len(matrix) == len(record_ids)):
            raise RuntimeError("record-list response has mismatched data and record_id_list lengths")
        return [{"record_id": record_id, "fields": dict(zip(fields, row))}
                for record_id, row in zip(record_ids, matrix)]
    candidates = []
    for key in ("items", "records"):
        candidates.extend(list(walk_values(response, key)))
    for candidate in candidates:
        if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):
            if not candidate or any("record_id" in item or "fields" in item for item in candidate):
                return candidate
    return []


def list_records(base_token, table_id, key=None):
    offset, result = 0, []
    while True:
        args = ["base", "+record-list", "--base-token", base_token, "--table-id", table_id,
                "--limit", "200", "--offset", str(offset)]
        if key:
            args.extend(["--field-id", key])
        response = cli_json(args)
        page = records_from_response(response)
        result.extend(page)
        has_more = bool(first_value(response, "has_more"))
        if not has_more:
            return result
        if not page:
            raise RuntimeError("record list indicated another page but returned no records")
        offset += len(page)


def field_items(response):
    data = response.get("data", {}) if isinstance(response, dict) else {}
    direct_fields = data.get("fields")
    if isinstance(direct_fields, list) and all(isinstance(field, dict) for field in direct_fields):
        return direct_fields
    for item in walk_values(response, "items"):
        if isinstance(item, list) and all(isinstance(entry, dict) for entry in item):
            if not item or "field_name" in item[0] or "type" in item[0]:
                return item
    return []


def target_field_map(base_token, table_id):
    fields = field_items(cli_json(["base", "+field-list", "--base-token", base_token, "--table-id", table_id]))
    return {str(field.get("field_name") or field.get("name")): field for field in fields}


def infer_field_type(series):
    values = [value for value in series.tolist() if not pd.isna(value)]
    if not values:
        return "text"
    if pd.api.types.is_bool_dtype(series):
        return "checkbox"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    text_values = [str(value).strip().lower() for value in values]
    boolean_values = set(["true", "false", "yes", "no", "y", "n", "1", "0", "是", "否"])
    if all(value in boolean_values for value in text_values):
        return "checkbox"
    date_pattern = r"^\d{4}([-/.年])\d{1,2}([-/.月])\d{1,2}(日)?([ T]\d{1,2}:\d{2}(:\d{2})?)?$"
    if all(pd.notna(pd.to_datetime(value, errors="coerce")) for value in text_values) and all(re.match(date_pattern, value) for value in text_values):
        return "datetime"
    numeric_pattern = r"^-?(0|[1-9]\d*)(\.\d+)?$"
    if all(re.match(numeric_pattern, value) for value in text_values):
        return "number"
    return "text"


def missing_field_specs(frame, field_map):
    return [{"name": column, "type": infer_field_type(frame[column])}
            for column in frame.columns if column not in field_map]


def assert_writable_fields(field_map, columns):
    bad = []
    for column in columns:
        field_type = str(field_map[column].get("type", "")).lower()
        if field_type and field_type not in WRITABLE_TYPES:
            bad.append("{0} ({1})".format(column, field_type))
    if bad:
        raise ValueError("unsupported or read-only target fields: {0}".format(", ".join(bad)))


def create_fields(base_token, table_id, specs):
    for spec in specs:
        cli_json(["base", "+field-create", "--base-token", base_token, "--table-id", table_id,
                  "--json", json.dumps(spec, ensure_ascii=False)])
        print("Created missing field: {0} ({1})".format(spec["name"], spec["type"]))


def adapt_value(value, field_type, column, row_number):
    if value is None or pd.isna(value):
        return None
    field_type = str(field_type).lower()
    if field_type in ("text", "date"):
        return str(value)
    if field_type == "number":
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            raise ValueError("row {0}, field {1} cannot be converted to number: {2}".format(row_number, column, value))
    if field_type == "datetime":
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError("row {0}, field {1} cannot be converted to datetime: {2}".format(row_number, column, value))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    if field_type in ("checkbox", "bool"):
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ("true", "yes", "y", "1", "是"):
            return True
        if text in ("false", "no", "n", "0", "否"):
            return False
        raise ValueError("row {0}, field {1} cannot be converted to checkbox: {2}".format(row_number, column, value))
    raise ValueError("field {0} has unsupported type: {1}".format(column, field_type))


def adapt_records(frame, field_map):
    records = []
    for row_number, (_, row) in enumerate(frame.iterrows(), 2):
        record = {}
        for column in frame.columns:
            field_type = field_map[column].get("type", "text")
            record[column] = adapt_value(row[column], field_type, column, row_number)
        records.append(record)
    return records


def remote_key_map(records, key):
    mapping = {}
    for record in records:
        fields = record.get("fields", record)
        value = fields.get(key)
        if isinstance(value, list):
            value = ",".join(str(part) for part in value)
        if value is None or str(value).strip() == "":
            continue
        value = key_token(value)
        record_id = record.get("record_id")
        if not record_id:
            raise RuntimeError("record-list response did not include record_id")
        if value in mapping:
            raise ValueError("target table has duplicate key: {0}".format(value))
        mapping[value] = record_id
    return mapping


def chunk(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def apply_sync(base_token, table_id, records, key, target_keys):
    creates = [record for record in records if key_token(record[key]) not in target_keys]
    updates = [record for record in records if key_token(record[key]) in target_keys]
    for batch in chunk(creates, 200):
        columns = list(batch[0].keys())
        cli_json(["base", "+record-batch-create", "--base-token", base_token, "--table-id", table_id,
                  "--json", json.dumps({"fields": columns, "rows": [[record[column] for column in columns] for record in batch]}, ensure_ascii=False)])
    for record in updates:
        cli_json(["base", "+record-upsert", "--base-token", base_token, "--table-id", table_id,
                  "--record-id", target_keys[key_token(record[key])], "--json", json.dumps(record, ensure_ascii=False)])
    return len(creates), len(updates)


def verify_keys(base_token, table_id, key, expected):
    actual = remote_key_map(list_records(base_token, table_id, key), key)
    missing = sorted(set(key_token(value) for value in expected) - set(actual))
    if missing:
        raise RuntimeError("write verification failed; missing keys: {0}".format(", ".join(missing[:10])))


def create_base(frame, app_name, table_name, apply):
    schema = [{"name": column, "type": infer_field_type(frame[column])} for column in frame.columns]
    print("Create preview: Base={0}, table={1}, fields={2}, rows={3}".format(app_name, table_name, len(schema), len(frame)))
    if not apply:
        print("Preview only. Re-run with --apply to create the Base and write rows.")
        return
    response = cli_json(["base", "+base-create", "--name", app_name, "--table-name", table_name,
                         "--fields", json.dumps(schema, ensure_ascii=False), "--time-zone", "Asia/Shanghai"])
    base_token = first_value(response, "base_token", "token")
    table_id = first_value(response, "table_id")
    if not base_token or not table_id:
        raise RuntimeError("Base creation response did not include base_token and table_id")
    records = adapt_records(frame, {spec["name"]: spec for spec in schema})
    for batch in chunk(records, 200):
        columns = list(frame.columns)
        cli_json(["base", "+record-batch-create", "--base-token", base_token, "--table-id", table_id,
                  "--json", json.dumps({"fields": columns, "rows": [[record[column] for column in columns] for record in batch]}, ensure_ascii=False)])
    print("Created Base: {0}; table: {1}; inserted rows: {2}".format(base_token, table_id, len(records)))


def sync(frame, url, key, apply, missing_fields_mode):
    if key not in frame.columns:
        raise ValueError("key column not found in source: {0}".format(key))
    base_token, table_id = resolve_base(url)
    if not table_id:
        raise ValueError("URL must identify one target table (include ?table=tbl...)" )
    field_map = target_field_map(base_token, table_id)
    missing_specs = missing_field_specs(frame, field_map)
    missing_names = [spec["name"] for spec in missing_specs]
    if missing_specs:
        summary = ", ".join("{0} ({1})".format(spec["name"], spec["type"]) for spec in missing_specs)
        if missing_fields_mode == "prompt":
            print("Missing target fields: {0}".format(summary))
            print("No data was written. Re-run with --missing-fields skip to ignore them, or --missing-fields create --apply to create them before importing.")
            return
        if missing_fields_mode == "skip":
            if key in missing_names:
                raise ValueError("cannot skip the key field: {0}".format(key))
            print("Skipping missing target fields: {0}".format(summary))
            frame = frame[[column for column in frame.columns if column not in missing_names]]
        elif apply:
            create_fields(base_token, table_id, missing_specs)
            field_map = target_field_map(base_token, table_id)
        else:
            print("Will create missing target fields on apply: {0}".format(summary))
            for spec in missing_specs:
                field_map[spec["name"]] = spec
    assert_writable_fields(field_map, list(frame.columns))
    records = adapt_records(frame, field_map)
    ensure_unique_keys(records, key, "source")
    target_keys = remote_key_map(list_records(base_token, table_id, key), key)
    create_count = sum(1 for record in records if key_token(record[key]) not in target_keys)
    update_count = len(records) - create_count
    print("Sync preview: target={0}/{1}; source={2}; create={3}; update={4}; remote rows={5}".format(base_token, table_id, len(records), create_count, update_count, len(target_keys)))
    if not apply:
        print("Preview only. Re-run with --apply after confirming these counts.")
        return
    created, updated = apply_sync(base_token, table_id, records, key, target_keys)
    verify_keys(base_token, table_id, key, [record[key] for record in records])
    print("Sync complete and verified: created={0}, updated={1}".format(created, updated))


def export_table(url, table_name, output):
    base_token, resolved_table_id = resolve_base(url)
    table_id = resolved_table_id or table_name
    if not table_id:
        raise ValueError("provide --table-name when the URL does not identify a table")
    rows = list_records(base_token, table_id)
    data = [record.get("fields", record) for record in rows]
    frame = pd.DataFrame(data)
    if output.lower().endswith(".csv"):
        frame.to_csv(output, index=False, encoding="utf-8-sig")
    elif output.lower().endswith(".xlsx"):
        frame.to_excel(output, index=False)
    else:
        raise ValueError("output must end in .csv or .xlsx")
    print("Exported {0} rows to {1}".format(len(frame), output))


def main():
    parser = argparse.ArgumentParser(description="Safe Excel/CSV and Feishu Base synchronizer")
    subparsers = parser.add_subparsers(dest="mode")
    create = subparsers.add_parser("create")
    create.add_argument("--input", required=True)
    create.add_argument("--app-name", required=True)
    create.add_argument("--table-name", required=True)
    create.add_argument("--apply", action="store_true")
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--input", required=True)
    sync_parser.add_argument("--url", required=True)
    sync_parser.add_argument("--key", required=True)
    sync_parser.add_argument("--apply", action="store_true")
    sync_parser.add_argument("--missing-fields", choices=["prompt", "skip", "create"], default="prompt",
                             help="when source fields are absent from the target: prompt (default), skip, or create")
    export = subparsers.add_parser("export")
    export.add_argument("--url", required=True)
    export.add_argument("--table-name")
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.mode:
        parser.print_help()
        return 2
    try:
        if args.mode == "create":
            create_base(read_frame(args.input), args.app_name, args.table_name, args.apply)
        elif args.mode == "sync":
            sync(read_frame(args.input), args.url, args.key, args.apply, args.missing_fields)
        else:
            export_table(args.url, args.table_name, args.output)
    except Exception as error:
        print("ERROR: {0}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
