# install-skills.ps1 —— WorkBuddy 技能自动安装(Windows / PowerShell)
# 用法:
#   右键"使用 PowerShell 运行"，或直接双击同目录的 install-skills.cmd
#   指定备份包:  install-skills.ps1 -Archive "D:\skills-backup-latest.tar.gz"
#   整目录替换:  install-skills.ps1 -Replace
#   装依赖:      install-skills.ps1 -Deps
#   装完自动重启: install-skills.ps1 -Restart
#   免交互给Key: $env:TAVILY_API_KEY="xxx"; install-skills.ps1
param(
  [string]$Archive = "",
  [switch]$Replace,
  [switch]$Deps,
  [switch]$Restart,
  [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
function Info($m){ Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "[✓] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "[!] $m" -ForegroundColor Yellow }
function Err($m){ Write-Host "[✗] $m" -ForegroundColor Red }

$mode = if ($Replace) { "replace" } else { "merge" }

# ---------- 定位技能源目录 ----------
if ($Archive -ne "") {
  if (-not (Test-Path $Archive)) { Err "备份包不存在: $Archive"; exit 1 }
  $tmp = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ("skills_restore_" + [guid]::NewGuid())) | Select-Object -ExpandProperty FullName
  Info "解压备份包 $Archive ..."
  tar.exe -xzf $Archive -C $tmp
  $src = Join-Path $tmp "skills"
  if (-not (Test-Path $src)) { Err "备份包内未找到 skills/"; exit 1 }
} else {
  $src = Split-Path -Parent $MyInvocation.MyCommand.Definition
}

$target = Join-Path $env:USERPROFILE ".workbuddy\skills"
New-Item -ItemType Directory -Force -Path $target | Out-Null

# ---------- 复制技能 ----------
if ($mode -eq "replace") {
  Warn "整目录替换模式：将清空 $target 后写入"
  Remove-Item -Recurse -Force $target
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -Recurse -Force "$src\*" $target
  Ok "已替换并写入全部技能(含 .git 历史)"
} else {
  Info "合并模式：仅复制不存在的文件，不覆盖已有技能"
  # robocopy /E 含空目录；/XX 不覆盖已存在的文件
  robocopy.exe "$src" "$target" /E /XX /NFL /NDL /NJH /NJS | Out-Null
  Ok "技能已合并到 $target"
}

# ---------- 还原 Tavily 密钥 ----------
$tavilyDir = Join-Path $target "tavily-search__skillhub"
if (Test-Path $tavilyDir) {
  $cfg = Join-Path $tavilyDir "config.json"
  $hasKey = $false
  if (Test-Path $cfg) {
    try { $j = Get-Content $cfg -Raw | ConvertFrom-Json; if ($j.api_key) { $hasKey = $true } } catch {}
  }
  if ($hasKey) {
    Ok "Tavily config.json 已存在，跳过密钥写入"
  } else {
    $key = $env:TAVILY_API_KEY
    if (-not $key) {
      Write-Host ""
      Warn "Tavily 搜索技能需 API Key 才能用(不填则留空占位)。"
      $key = Read-Host "请输入 Tavily API Key(留空跳过)"
    }
    if ($key) {
      @{ api_key = $key } | ConvertTo-Json | Set-Content -Path $cfg -Encoding UTF8
      Ok "已写入 Tavily 密钥到 config.json"
    } else {
      Warn "未提供密钥，已跳过。手动编辑: $cfg  ->  {""api_key"": ""你的tvly-...key""}"
    }
  }
}

# ---------- 依赖检测 / 可选安装 ----------
$pyReqs = Get-ChildItem -Path $target -Recurse -Filter requirements.txt | Where-Object { $_.FullName -notmatch 'node_modules' }
$npmPkgs = Get-ChildItem -Path $target -Recurse -Filter package.json | Where-Object { $_.FullName -notmatch 'node_modules' }
if (($pyReqs.Count -eq 0) -and ($npmPkgs.Count -eq 0)) {
  Ok "未发现需要额外安装的 Python/Node 依赖"
} else {
  Info "检测到依赖声明："
  $pyReqs | ForEach-Object { Write-Host "    - Python: $($_.FullName)" }
  $npmPkgs | ForEach-Object { Write-Host "    - Node:   $($_.FullName)" }
  if ($Deps) {
    foreach ($f in $pyReqs) {
      Info "pip install -r $($f.FullName)"
      if (Get-Command python -ErrorAction SilentlyContinue) { & python -m pip install -r $f.FullName 2>&1 | Out-Null }
      elseif (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 -m pip install -r $f.FullName 2>&1 | Out-Null }
      else { Warn "未找到 python，跳过 $($f.FullName)" }
    }
    foreach ($f in $npmPkgs) {
      $d = $f.DirectoryName
      Info "npm install in $d"
      if (Get-Command npm -ErrorAction SilentlyContinue) { Push-Location $d; & npm install 2>&1 | Out-Null; Pop-Location }
      else { Warn "未找到 npm，跳过 $d" }
    }
  } else {
    Warn "未启用 -Deps，未自动安装。重跑加 -Deps 即可安装。"
  }
}

# ---------- 自动重启 WorkBuddy(默认关闭，需 -Restart) ----------
$doRestart = $Restart -and (-not $NoRestart)
if ($doRestart) {
  Info "尝试重启 WorkBuddy ..."
  $proc = @(Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue)
  if ($proc.Count -eq 0) { $proc = @(Get-Process -Name "CodeBuddy*" -ErrorAction SilentlyContinue) }
  if ($proc.Count -gt 0) {
    $p = $proc[0]
    $exe = $p.Path
    Stop-Process -Force -Id $p.Id
    Start-Sleep -Seconds 2
    if ($exe -and (Test-Path $exe)) { Start-Process $exe; Ok "已重启 WorkBuddy" }
    else { Warn "找不到 exe 路径，请手动启动 WorkBuddy" }
  } else {
    Warn "未检测到运行中的 WorkBuddy，请手动启动"
  }
} else {
  Write-Host ""
  Ok "技能安装完成！"
  Info "请重启 WorkBuddy 使技能生效(或重跑加 -Restart 自动重启)。"
}

# 清理临时解压目录
if ($Archive -ne "" -and (Test-Path $tmp)) { Remove-Item -Recurse -Force $tmp }
