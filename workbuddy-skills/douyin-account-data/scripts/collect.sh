#!/usr/bin/env bash

set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
skill_dir="$(CDPATH= cd -- "$script_dir/.." && pwd -P)"
dashboard_root="${PERSONAL_DASHBOARD_ROOT:-}"
vault_root="${PERSONAL_DASHBOARD_VAULT_ROOT:-}"
work_ids=""
cycle_stamp="$(date '+%Y%m%d-%H%M%S')"
temp_root=""
store_stage=""

usage() {
  printf 'usage: %s --dashboard-root PATH --vault-root PATH [--work-ids ID,ID]\n' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dashboard-root)
      dashboard_root="${2:-}"
      shift 2
      ;;
    --vault-root)
      vault_root="${2:-}"
      shift 2
      ;;
    --work-ids)
      work_ids="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf 'status=unsupported_platform\n' >&2
  printf 'message=This entry point requires macOS and Ego Lite. On Windows, use scripts/collect_playwright.py instead.\n' >&2
  exit 20
fi

if [[ -z "$dashboard_root" || -z "$vault_root" ]]; then
  printf 'Both --dashboard-root and --vault-root are required.\n' >&2
  usage >&2
  exit 64
fi

dashboard_root="$(CDPATH= cd -- "$dashboard_root" && pwd -P)"
vault_root="$(CDPATH= cd -- "$vault_root" && pwd -P)"
workbench_root="$dashboard_root/Workbench"
store_parent="$vault_root/30_self_media"
store_root="$store_parent/douyin"

if [[ ! -f "$workbench_root/server/vault-index.mjs" ]]; then
  printf 'Workbench parser not found: %s\n' "$workbench_root/server/vault-index.mjs" >&2
  exit 66
fi

for command_name in ego-browser node python3 jq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing dependency: %s\n' "$command_name" >&2
    exit 69
  fi
done

if ! python3 -c 'import openpyxl' >/dev/null 2>&1; then
  printf 'missing Python dependency: openpyxl\n' >&2
  exit 69
fi

if [[ -n "$work_ids" && ! "$work_ids" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
  printf 'invalid --work-ids value\n' >&2
  exit 65
fi

cleanup() {
  if [[ -n "$temp_root" ]]; then
    case "$temp_root" in
      */personal-workbench-douyin.*) rm -rf -- "$temp_root" ;;
    esac
  fi
  if [[ -n "$store_stage" ]]; then
    case "$store_stage" in
      "$store_parent"/.douyin-staging.*) rm -rf -- "$store_stage" ;;
    esac
  fi
  bash "$script_dir/ego_collect.sh" complete >/dev/null 2>&1 || true
}
trap cleanup EXIT

record_failure() {
  local status="$1"
  local message="$2"
  if [[ -d "$store_root" ]]; then
    node "$script_dir/publish_workbench_data.mjs" \
      --vault "$vault_root" \
      --output "$store_root" \
      --failure-status "$status" \
      --failure-message "$message" >/dev/null || true
  fi
}

if ! bash "$script_dir/ego_collect.sh" probe; then
  record_failure "blocked_auth" "Ego Lite is not logged into Douyin Creator Center"
  printf 'status=blocked_auth\n' >&2
  printf 'action=Open Ego Lite, sign in to your own Douyin Creator Center, then retry.\n' >&2
  exit 21
fi

if [[ -z "$work_ids" && -s "$store_root/works.csv" ]]; then
  work_ids="$(python3 - "$store_root/works.csv" <<'PY'
import csv
import sys

with open(sys.argv[1], encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
ids = []
for row in rows:
    value = str(row.get("平台作品ID", "")).strip()
    if value.isdigit() and value not in ids:
        ids.append(value)
print(",".join(ids))
PY
)"
fi

temp_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-workbench-douyin.XXXXXX")"
snapshot_root="$temp_root/${cycle_stamp}-creator-collector"
exports_dir="$snapshot_root/00_exports"
snapshots_dir="$snapshot_root/01_page_snapshots"
inventory_dir="$snapshot_root/02_inventory"
analysis_dir="$temp_root/analysis"
mkdir -p "$analysis_dir"

collector_status=0
DOUYIN_WORK_IDS="$work_ids" bash "$script_dir/ego_collect.sh" \
  collect-weekly "$exports_dir" "$snapshots_dir" || collector_status=$?

manifest="$exports_dir/run_manifest.json"
manifest_result=""
if [[ -s "$manifest" ]]; then
  manifest_result="$(jq -r '.result // empty' "$manifest")"
fi
if [[ "$collector_status" -ne 0 || "$manifest_result" != "complete" ]]; then
  record_failure "collection_failed" "Douyin Creator Center collection did not complete"
  printf 'status=collection_failed\n' >&2
  exit 22
fi

if ! find "$exports_dir" -maxdepth 1 -type f -name '*.xlsx' -print -quit | grep -q .; then
  record_failure "collection_failed" "No official Excel exports were downloaded"
  printf 'status=collection_failed\n' >&2
  exit 22
fi

python3 "$script_dir/inventory_exports.py" \
  --input "$exports_dir" \
  --output "$inventory_dir"

previous_args=()
if [[ -s "$store_root/works.csv" ]]; then
  previous_args=(--previous "$store_root/works.csv")
fi

python3 "$script_dir/analyze_snapshot.py" \
  --vault-root "$vault_root" \
  --config "$skill_dir/assets/config.example.json" \
  --snapshot "$snapshot_root" \
  "${previous_args[@]}" \
  --output "$analysis_dir" \
  --no-workflow-writeback \
  --no-latest-pointer \
  --published-source-root "30_self_media/douyin" \
  --published-work-list "30_self_media/douyin/works.csv" \
  --published-previous "30_self_media/douyin/work-history.csv"

quality_status="$(jq -r '.data_quality.status // empty' "$analysis_dir/analysis.json")"
if [[ -z "$quality_status" || "$quality_status" == "failed" ]]; then
  record_failure "data_quality_failed" "Douyin data quality gate failed"
  printf 'status=data_quality_failed\n' >&2
  exit 23
fi

mkdir -p "$store_parent"
store_stage="$(mktemp -d "$store_parent/.douyin-staging.XXXXXX")"
existing_args=()
if [[ -s "$store_root/current.json" ]]; then
  existing_args=(--existing "$store_root/current.json")
fi

node "$script_dir/publish_workbench_data.mjs" \
  --vault "$vault_root" \
  --workbench-root "$workbench_root" \
  --snapshot "$snapshot_root" \
  --analysis "$analysis_dir/analysis.json" \
  --output "$store_stage" \
  "${existing_args[@]}"

backup_root="$store_parent/.douyin-backup-$cycle_stamp-$$"
if [[ -e "$backup_root" ]]; then
  printf 'refusing existing backup path: %s\n' "$backup_root" >&2
  exit 67
fi
if [[ -d "$store_root" ]]; then
  mv "$store_root" "$backup_root"
fi
if mv "$store_stage" "$store_root"; then
  store_stage=""
  if [[ -d "$backup_root" ]]; then
    rm -rf -- "$backup_root"
  fi
else
  if [[ -d "$backup_root" && ! -d "$store_root" ]]; then
    mv "$backup_root" "$store_root"
  fi
  exit 68
fi

node "$script_dir/publish_workbench_data.mjs" \
  --vault "$vault_root" \
  --workbench-root "$workbench_root" \
  --output "$store_root" \
  --verify

node --input-type=module - "$store_root/current.json" <<'NODE'
import fs from "node:fs";

const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const analytics = data.douyin?.analytics ?? {};
console.log(JSON.stringify({
  status: "complete",
  current: process.argv[2],
  capturedAt: data.capturedAt,
  quality: data.dataQuality?.status,
  works: data.douyin?.works?.length ?? 0,
  deepWorkDetails: Object.keys(analytics.workDetails ?? {}).length,
  accountDailyRows: analytics.account?.daily?.length ?? 0,
  collections: analytics.collections?.length ?? 0,
  temporarySourcesDeleted: true
}, null, 2));
NODE
