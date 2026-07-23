#!/usr/bin/env bash
#
# WorkBuddy 技能自动安装脚本
# ---------------------------------------------------------------
# 用法(三选一):
#   1) 解压 skills-backup-*.tar.gz 后，在本目录运行:
#        bash install-skills.sh
#   2) 直接指定备份包路径:
#        bash install-skills.sh /path/to/skills-backup-latest.tar.gz
#   3) 带环境变量免交互(适合无人值守):
#        TAVILY_API_KEY=xxx bash install-skills.sh
#
# 选项:
#   --replace   整目录替换目标 skills(会覆盖新机已有技能与 .git 历史)
#   --deps      自动安装各技能的 Python/Node 依赖(需联网，默认只提示不装)
#   -h|--help   显示帮助
#
set -euo pipefail

# ---------- 颜色 ----------
if [ -t 1 ]; then
  C_GREEN=$'\033[0;32m'; C_YEL=$'\033[0;33m'; C_RED=$'\033[0;31m'; C_CYAN=$'\033[0;36m'; C_RST=$'\033[0m'
else
  C_GREEN=""; C_YEL=""; C_RED=""; C_CYAN=""; C_RST=""
fi
info()  { echo "${C_CYAN}[*]${C_RST} $*"; }
ok()    { echo "${C_GREEN}[✓]${C_RST} $*"; }
warn()  { echo "${C_YEL}[!]${C_RST} $*"; }
err()   { echo "${C_RED}[✗]${C_RST} $*"; }

MODE="merge"          # merge | replace
INSTALL_DEPS=0
ARCHIVE=""

for a in "$@"; do
  case "$a" in
    --replace) MODE="replace" ;;
    --deps)    INSTALL_DEPS=1 ;;
    -h|--help) sed -n '3,18p' "$0"; exit 0 ;;
    *) ARCHIVE="$a" ;;
  esac
done

# ---------- 定位技能源目录 ----------
# 若给定备份包：先解压到临时目录，再从临时目录取 skills/
# 否则：假定脚本就在 skills/ 目录内，用脚本自身所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$ARCHIVE" ]; then
  if [ ! -f "$ARCHIVE" ]; then err "备份包不存在: $ARCHIVE"; exit 1; fi
  TMP="$(mktemp -d)"
  info "解压备份包 $ARCHIVE ..."
  tar -xzf "$ARCHIVE" -C "$TMP"
  SRC="$TMP/skills"
  [ -d "$SRC" ] || { err "备份包内未找到 skills/ 目录"; exit 1; }
else
  SRC="$SCRIPT_DIR"
fi

TARGET="${HOME}/.workbuddy/skills"
mkdir -p "$TARGET"

# ---------- 复制技能 ----------
if [ "$MODE" = "replace" ]; then
  warn "整目录替换模式：将清空 $TARGET 后写入备份内容"
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
  cp -r "$SRC/." "$TARGET/"
  ok "已替换并写入全部技能(含 .git 历史)"
else
  info "合并模式：仅复制不存在的文件，不覆盖新机已有技能"
  cp -rn "$SRC/." "$TARGET/" 2>/dev/null || cp -r "$SRC/." "$TARGET/"
  ok "技能已合并到 $TARGET"
fi

# ---------- 还原 Tavily 密钥 ----------
TAVILY_DIR="$TARGET/tavily-search__skillhub"
if [ -d "$TAVILY_DIR" ]; then
  if [ -f "$TAVILY_DIR/config.json" ] && grep -q '"api_key"' "$TAVILY_DIR/config.json" 2>/dev/null; then
    ok "Tavily config.json 已存在，跳过密钥写入"
  else
    KEY="${TAVILY_API_KEY:-}"
    if [ -z "$KEY" ]; then
      echo
      warn "Tavily 搜索技能需要 API Key 才能使用(不填则留空占位，之后可手动补)。"
      printf "请输入 Tavily API Key (留空跳过): "
      read -r KEY || KEY=""
    fi
    if [ -n "$KEY" ]; then
      printf '{\n  "api_key": "%s"\n}\n' "$KEY" > "$TAVILY_DIR/config.json"
      ok "已写入 Tavily 密钥到 config.json"
    else
      warn "未提供密钥，已跳过。如需使用 tavily 搜索，请手动编辑:"
      warn "      $TAVILY_DIR/config.json"
      warn '      内容: {"api_key": "你的tvly-...key"}'
    fi
  fi
fi

# ---------- 依赖检测 / 可选安装 ----------
echo
info "检测技能依赖 ..."
declare -a PY_REQS NPM_PKGS
while IFS= read -r f; do PY_REQS+=("$f"); done < <(find "$TARGET" -name requirements.txt -not -path '*/node_modules/*' 2>/dev/null)
while IFS= read -r f; do NPM_PKGS+=("$f"); done < <(find "$TARGET" -name package.json -not -path '*/node_modules/*' 2>/dev/null)

if [ "${#PY_REQS[@]}" -eq 0 ] && [ "${#NPM_PKGS[@]}" -eq 0 ]; then
  ok "未发现需要额外安装的 Python/Node 依赖"
else
  echo "  发现以下依赖声明："
  for f in "${PY_REQS[@]}"; do echo "    - Python: $f"; done
  for f in "${NPM_PKGS[@]}"; do echo "    - Node:   $f"; done
  if [ "$INSTALL_DEPS" -eq 1 ]; then
    for f in "${PY_REQS[@]}"; do
      d="$(dirname "$f")"
      info "pip install -r $f"
      ( command -v python3 >/dev/null && cd "$d" && python3 -m pip install -r "$(basename "$f")" ) \
        || ( command -v pip >/dev/null && cd "$d" && pip install -r "$(basename "$f")" ) \
        || warn "pip 不可用，跳过 $f"
    done
    for f in "${NPM_PKGS[@]}"; do
      d="$(dirname "$f")"
      info "npm install in $d"
      ( command -v npm >/dev/null && cd "$d" && npm install ) || warn "npm 不可用，跳过 $d"
    done
  else
    warn "未启用 --deps，未自动安装。如需安装，重跑: bash install-skills.sh --deps"
  fi
fi

# ---------- 收尾 ----------
echo
ok "技能安装完成！"
info "下一步：重启 WorkBuddy，技能即可在对话中使用。"
warn "注意：联网类技能若需各自的 API Key，请在对应 config.json 中补充。"

# 清理临时解压目录
[ -n "${TMP:-}" ] && rm -rf "$TMP"
