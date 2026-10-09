#!/usr/bin/env bash

set -euo pipefail

mode="${1:-probe}"
output_dir="${2:-}"
snapshot_dir="${3:-}"
work_ids="${DOUYIN_WORK_IDS:-}"
task_space="douyin creator data"

if [[ "$mode" != "probe" && "$mode" != "collect-weekly" && "$mode" != "complete" ]]; then
  printf 'usage: %s [probe|collect-weekly|complete] [OUTPUT_DIR] [SNAPSHOT_DIR]\n' "$0" >&2
  exit 64
fi

if [[ "$mode" == "collect-weekly" ]]; then
  case "$output_dir" in
    /tmp/douyin-feedback.*/*/00_exports) ;;
    *)
      printf 'refusing non-temporary output path: %s\n' "$output_dir" >&2
      exit 65
      ;;
  esac
  case "$snapshot_dir" in
    /tmp/douyin-feedback.*/*/01_page_snapshots) ;;
    *)
      printf 'refusing non-temporary snapshot path: %s\n' "$snapshot_dir" >&2
      exit 65
      ;;
  esac
  if [[ -n "$work_ids" && ! "$work_ids" =~ ^[0-9]+(,[0-9]+)*$ ]]; then
    printf 'invalid DOUYIN_WORK_IDS: %s\n' "$work_ids" >&2
    exit 65
  fi
  mkdir -p "$output_dir" "$snapshot_dir"
fi

if [[ "$mode" == "complete" ]]; then
  ego-browser nodejs <<'EOF'
const spaces = await listTaskSpaces()
const target = spaces.find((item) => item.name === 'douyin creator data' || item.taskId === 'douyin creator data')
if (target) {
  const result = await completeTaskSpace(target.id, { keep: false })
  cliLog(JSON.stringify({ ok: Boolean(result?.done), taskSpaceId: target.id, result }))
} else {
  cliLog(JSON.stringify({ ok: true, skipped: 'task-space-not-found' }))
}
EOF
  exit 0
fi

config_json="$(node -e '
  const workIds = process.argv[4].split(",").map((value) => value.trim()).filter(Boolean);
  process.stdout.write(JSON.stringify({
    mode: process.argv[1],
    outputDir: process.argv[2],
    snapshotDir: process.argv[3],
    workIds
  }));
' "$mode" "$output_dir" "$snapshot_dir" "$work_ids")"

set +e
{
  printf 'const injectedConfig = %s\n' "$config_json"
  cat <<'EOF'
const fs = await import('node:fs')
const path = await import('node:path')
const crypto = await import('node:crypto')

const config = injectedConfig
const outputDir = config.outputDir
const mode = config.mode
const snapshotDir = config.snapshotDir
const requestedWorkIds = Array.isArray(config.workIds) ? config.workIds : []
const taskSpaceName = 'douyin creator data'
const HOME_URL = 'https://creator.douyin.com/creator-micro/home'
const OPERATION_URL = 'https://creator.douyin.com/creator-micro/data-center/operation'
const CONTENT_URL = 'https://creator.douyin.com/creator-micro/data-center/content'
const WORK_LIST_URL = 'https://creator.douyin.com/creator-micro/content/manage?enter_from=publish'
const results = []

const task = await useOrCreateTaskSpace(taskSpaceName)
await openOrReuseTab(CONTENT_URL, { wait: true, timeout: 30 })

function safeFileName(value) {
  const cleaned = String(value || 'download.bin')
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
  return cleaned || 'download.bin'
}

function uniquePath(dir, name) {
  const parsed = path.parse(safeFileName(name))
  let candidate = path.join(dir, parsed.base)
  let index = 2
  while (fs.existsSync(candidate)) {
    candidate = path.join(dir, parsed.name + '-' + index + parsed.ext)
    index += 1
  }
  return candidate
}

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex')
}

async function bodyText() {
  return String(await js(String.raw`document.body?.innerText || ''`))
}

async function loginState() {
  const info = await pageInfo()
  const text = await bodyText()
  const loggedIn =
    String(info.url || '').includes('creator.douyin.com/creator-micro/') &&
    !String(info.url || '').includes('/login') &&
    /账号总览|作品分析|粉丝分析|内容管理|数据中心/.test(text) &&
    !/扫码登录|登录后即可|登录\/注册/.test(text)
  return {
    ok: loggedIn,
    browserEngine: 'ego-browser',
    taskSpaceId: task.id,
    title: info.title,
    url: info.url,
    textSample: text.replace(/\s+/g, ' ').trim().slice(0, 500)
  }
}

async function waitForReady(timeoutSeconds = 60) {
  const deadline = Date.now() + timeoutSeconds * 1000
  let state = await loginState()
  while (!state.ok && Date.now() < deadline) {
    await wait(1)
    state = await loginState()
  }
  return state
}

async function gotoReady(url) {
  await gotoAndWait(url, { timeout: 120, settle: 2 })
  const state = await waitForReady(60)
  if (!state.ok) throw new Error('创作者中心未登录或页面未就绪：' + state.url)
  return state
}

async function visibleButtonCount(text, exact = false) {
  const needle = JSON.stringify(text)
  return Number(await js(`(() => {
    const needle = ${needle}
    return [...document.querySelectorAll('button')].filter((el) => {
      const rect = el.getBoundingClientRect()
      const value = (el.innerText || '').replace(/\\s+/g, ' ').trim()
      const matches = ${exact ? 'value === needle' : 'value.includes(needle)'}
      return matches && rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden'
    }).length
  })()`))
}

async function waitForButtonCount(text, expected, exact = false, timeoutSeconds = 30) {
  const deadline = Date.now() + timeoutSeconds * 1000
  let count = await visibleButtonCount(text, exact)
  while (count !== expected && Date.now() < deadline) {
    await wait(0.5)
    count = await visibleButtonCount(text, exact)
  }
  if (count !== expected) {
    throw new Error('按钮“' + text + '”预期 ' + expected + ' 个，实际为 ' + count + ' 个')
  }
}

async function clickRoleExact(role, label, timeoutSeconds = 30) {
  const roleJson = JSON.stringify(role)
  const labelJson = JSON.stringify(label)
  const deadline = Date.now() + timeoutSeconds * 1000
  let result = { ok: false, count: 0 }
  while (!result.ok && Date.now() < deadline) {
    result = await js(`(() => {
      const role = ${roleJson}
      const label = ${labelJson}
      const items = [...document.querySelectorAll('[role="' + role + '"]')].filter((el) => {
        const rect = el.getBoundingClientRect()
        const text = (el.innerText || '').replace(/\\s+/g, ' ').trim()
        return text === label && rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden'
      })
      if (items.length !== 1) return { ok: false, count: items.length }
      items[0].click()
      return { ok: true, count: 1 }
    })()`)
    if (!result.ok) await wait(0.5)
  }
  if (!result?.ok) throw new Error(role + '“' + label + '”预期唯一，实际为 ' + (result?.count ?? 0) + ' 个')
  await wait(0.7)
}

async function clickRadioLabel(label, index = 0, expectedCount = 1) {
  const labelJson = JSON.stringify(label)
  const result = await js(`(() => {
    const label = ${labelJson}
    const items = [...document.querySelectorAll('input[type="radio"]')].filter((el) => {
      const text = (el.parentElement?.parentElement?.innerText || '').replace(/\\s+/g, ' ').trim()
      return text === label
    })
    if (items.length !== ${expectedCount}) return { ok: false, count: items.length }
    const input = items[${index}]
    const target = input.parentElement?.parentElement || input
    target.click()
    return { ok: true, count: items.length, checked: input.checked }
  })()`)
  if (!result?.ok) {
    throw new Error('单选项“' + label + '”预期 ' + expectedCount + ' 个，实际为 ' + (result?.count ?? 0) + ' 个')
  }
  await wait(0.7)
}

async function capturePageSnapshot(label) {
  if (!snapshotDir) return null
  const info = await pageInfo()
  const snapshot = {
    schemaVersion: 1,
    capturedAt: new Date().toISOString(),
    label,
    title: info.title,
    url: info.url,
    bodyText: (await bodyText()).trim()
  }
  const target = uniquePath(snapshotDir, safeFileName(label) + '.json')
  fs.writeFileSync(target, JSON.stringify(snapshot, null, 2) + '\n')
  return target
}

async function downloadButton({ text, exact, index, label, sequence }) {
  const expected = index + 1
  const currentCount = await visibleButtonCount(text, exact)
  if (currentCount < expected) {
    throw new Error('下载按钮“' + text + '”索引 ' + index + ' 不存在，当前共 ' + currentCount + ' 个')
  }
  const before = new Set(fs.readdirSync(outputDir))
  const startedAt = new Date()
  const startedMs = Date.now()
  const textJson = JSON.stringify(text)
  const clickResult = await js(`(() => {
    const needle = ${textJson}
    const buttons = [...document.querySelectorAll('button')].filter((el) => {
      const rect = el.getBoundingClientRect()
      const value = (el.innerText || '').replace(/\\s+/g, ' ').trim()
      const matches = ${exact ? 'value === needle' : 'value.includes(needle)'}
      return matches && rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden'
    })
    if (!buttons[${index}]) return { ok: false, count: buttons.length }
    buttons[${index}].click()
    return { ok: true, count: buttons.length }
  })()`)
  if (!clickResult?.ok) throw new Error('下载按钮点击失败：' + label)

  const deadline = Date.now() + 120000
  let downloaded = null
  while (Date.now() < deadline) {
    const candidates = fs.readdirSync(outputDir).filter((name) =>
      !before.has(name) && !name.endsWith('.crdownload') && !name.endsWith('.manifest.json')
    )
    if (candidates.length > 0) {
      downloaded = path.join(outputDir, candidates[0])
      const firstSize = fs.statSync(downloaded).size
      await wait(0.5)
      if (fs.existsSync(downloaded) && fs.statSync(downloaded).size === firstSize && firstSize > 0) break
      downloaded = null
    }
    await wait(0.5)
  }
  if (!downloaded) throw new Error('等待下载超时：' + label)

  const prefixed = String(sequence).padStart(2, '0') + '-' + safeFileName(label) + '__' + path.basename(downloaded)
  const target = uniquePath(outputDir, prefixed)
  fs.renameSync(downloaded, target)
  const info = await pageInfo()
  const stat = fs.statSync(target)
  const record = {
    ok: true,
    label,
    startedAt: startedAt.toISOString(),
    capturedAt: new Date().toISOString(),
    elapsedMs: Date.now() - startedMs,
    source: { title: info.title, url: info.url, browserEngine: 'ego-browser' },
    file: { name: path.basename(target), path: target, bytes: stat.size, sha256: sha256File(target) },
    requestTrace: []
  }
  fs.writeFileSync(target + '.manifest.json', JSON.stringify(record, null, 2) + '\n')
  results.push(record)
  return record
}

async function collectVisibleExports(labels, startSequence, text = '导出数据', exact = false) {
  await waitForButtonCount(text, labels.length, exact)
  const records = []
  for (let index = 0; index < labels.length; index += 1) {
    records.push(await downloadButton({ text, exact, index, label: labels[index], sequence: startSequence + index }))
  }
  return records
}

if (mode === 'probe') {
  const state = await waitForReady(60)
  cliLog(JSON.stringify(state, null, 2))
  if (!state.ok) throw new Error('blocked_auth')
} else {
  fs.mkdirSync(outputDir, { recursive: true })
  fs.mkdirSync(snapshotDir, { recursive: true })
  await cdp('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: outputDir })

  const failures = []
  const snapshots = []
  const runStartedAt = new Date()
  let workIds = [...requestedWorkIds]

  async function runStep(name, fn) {
    try {
      await fn()
    } catch (error) {
      failures.push({ step: name, error: error instanceof Error ? error.message : String(error) })
    }
  }

  const initialState = await waitForReady(60)
  if (!initialState.ok) throw new Error('blocked_auth')

  await runStep('首页快照与作品发现', async () => {
    await gotoReady(HOME_URL)
    const snapshot = await capturePageSnapshot('首页-当前')
    if (snapshot) snapshots.push(snapshot)
    const discoveredWorkIds = await js(String.raw`(() => {
      const ids = []
      for (const anchor of document.querySelectorAll('a[href*="/work-management/work-detail/"]')) {
        const match = anchor.href.match(/work-detail\/(\d+)/)
        if (match && !ids.includes(match[1])) ids.push(match[1])
      }
      return ids
    })()`)
    workIds = [...new Set([...workIds, ...discoveredWorkIds])]
    if (workIds.length === 0) {
      const clicked = await js(String.raw`(() => {
        const items = [...document.querySelectorAll('a,button')].filter((el) => (el.innerText || '').trim() === '查看分析')
        if (items.length !== 1) return false
        items[0].click()
        return true
      })()`)
      if (clicked) {
        const deadline = Date.now() + 30000
        while (Date.now() < deadline) {
          const info = await pageInfo()
          const match = String(info.url || '').match(/work-detail\/(\d+)/)
          if (match) {
            workIds.push(match[1])
            break
          }
          await wait(0.5)
        }
      }
    }
    if (workIds.length === 0) throw new Error('首页未发现可用作品详情链接，且未提供 DOUYIN_WORK_IDS')
    return []
  })

  await runStep('账号数据总览', async () => {
    await gotoReady(OPERATION_URL)
    await waitForButtonCount('导出数据', 2, false)
    const records = []
    const periods = [
      { ui: '昨天', file: '昨日' },
      { ui: '近7天', file: '近7天' },
      { ui: '近30天', file: '近30天' }
    ]
    let sequence = 1
    for (const period of periods) {
      await clickRadioLabel(period.ui, 0, 2)
      records.push(await downloadButton({ text: '导出数据', exact: false, index: 0, label: period.file + '-作品数据表现', sequence }))
      sequence += 1
      await clickRadioLabel(period.ui, 1, 2)
      records.push(await downloadButton({ text: '导出数据', exact: false, index: 1, label: period.file + '-粉丝数据表现', sequence }))
      sequence += 1
    }
    return records
  })

  await runStep('投稿与合集', async () => {
    await gotoReady(CONTENT_URL)
    const records = []
    await clickRoleExact('tab', '投稿作品')
    await clickRadioLabel('投稿分析')
    records.push(...await collectVisibleExports(['投稿概览', '投稿表现'], 7))
    await clickRadioLabel('投稿列表')
    records.push(...await collectVisibleExports(['投稿列表'], 9))
    await clickRoleExact('tab', '合集')
    await clickRadioLabel('合集分析')
    records.push(...await collectVisibleExports(['合集概览', '合集表现'], 10))
    await clickRadioLabel('合集列表')
    records.push(...await collectVisibleExports(['合集列表'], 12))
    return records
  })

  await runStep('作品列表', async () => {
    await gotoReady(WORK_LIST_URL)
    return collectVisibleExports(['作品列表'], 13)
  })

  let nextSequence = 14
  for (const workId of workIds) {
    await runStep('作品详情 ' + workId, async () => {
      const url = 'https://creator.douyin.com/creator-micro/work-management/work-detail/' + workId + '?enter_from=homepage'
      await gotoReady(url)
      const records = []
      const plans = [
        { tab: '总览', labels: ['总览-流量数据', '总览-粉丝数据'] },
        { tab: '流量分析', labels: ['流量分析-内容吸引力', '流量分析-观众参与度', '流量分析-流量来源'] },
        { tab: '观众分析', labels: ['观众分析-观众数据'] }
      ]
      for (const plan of plans) {
        await clickRoleExact('tab', plan.tab)
        const snapshot = await capturePageSnapshot('作品-' + workId + '-' + plan.tab)
        if (snapshot) snapshots.push(snapshot)
        records.push(...await collectVisibleExports(plan.labels.map((label) => workId + '-' + label), nextSequence, '导出', true))
        nextSequence += plan.labels.length
      }
      try {
        await clickRoleExact('tab', '评论热词')
        const snapshot = await capturePageSnapshot('作品-' + workId + '-评论热词')
        if (snapshot) snapshots.push(snapshot)
      } catch {
        // 评论热词无官方 Excel，不阻断核心导出。
      }
      return records
    })
  }

  const completedAt = new Date()
  const manifest = {
    schemaVersion: 1,
    mode: 'weekly',
    startedAt: runStartedAt.toISOString(),
    completedAt: completedAt.toISOString(),
    elapsedMs: completedAt.getTime() - runStartedAt.getTime(),
    sourceUrl: CONTENT_URL,
    browserEngine: 'ego-browser',
    profileDir: 'ego-browser shared login state',
    taskSpaceId: task.id,
    result: failures.length === 0 ? 'complete' : results.length > 0 ? 'partial' : 'failed',
    successCount: results.length,
    failureCount: failures.length,
    workIds,
    files: results.map((item) => item.file),
    pageSnapshots: snapshots,
    failures
  }
  const manifestPath = path.join(outputDir, 'run_manifest.json')
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n')
  cliLog(JSON.stringify({ ok: failures.length === 0, manifestPath, ...manifest }, null, 2))
  if (failures.length > 0) throw new Error('collection_partial')
}
EOF
} | ego-browser nodejs
ego_status=$?
set -e

if [[ "$ego_status" -ne 0 ]]; then
  if [[ "$mode" == "probe" ]]; then
    exit 2
  fi
  exit 3
fi
