#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const STORE_RELATIVE = "30_self_media/douyin";
const REQUIRED_FILES = [
  "README.md",
  "current.json",
  "account-daily.csv",
  "works.csv",
  "work-history.csv",
  "work-details.json",
  "collections.csv",
  "analysis.json",
  "last-run.json",
];

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    if (key === "bootstrap" || key === "verify") {
      result[key] = true;
      continue;
    }
    result[key] = argv[index + 1];
    index += 1;
  }
  return result;
}

function ensure(value, message) {
  if (!value) throw new Error(message);
  return value;
}

function workKey(work) {
  return `${String(work?.publishedAt ?? "").slice(0, 16)}|${String(
    work?.title ?? "",
  )
    .replace(/#[^#\n]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase("zh-CN")}`;
}

function csvCell(value) {
  if (value == null) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function csvText(headers, rows) {
  return `\uFEFF${[headers, ...rows]
    .map((row) => row.map(csvCell).join(","))
    .join("\n")}\n`;
}

function pctDecimal(value) {
  return Number.isFinite(value) ? value / 100 : null;
}

function snapshotFromWork(work, capturedAt) {
  return {
    capturedAt,
    publishedAt: work.publishedAt ?? null,
    title: work.title ?? null,
    platformWorkId: work.platformWorkId ?? null,
    grain: "作品累计快照",
    views: work.views ?? null,
    likes: work.likes ?? null,
    shares: work.shares ?? null,
    comments: work.comments ?? null,
    saves: work.saves ?? null,
    profileVisits: work.profileVisits ?? null,
    followerGain: work.followerGain ?? null,
    sourcePath: `${STORE_RELATIVE}/work-history.csv`,
  };
}

function historyKey(item) {
  return `${item.capturedAt}|${String(item.publishedAt ?? "").slice(0, 16)}|${String(
    item.title ?? "",
  )}`;
}

function mergeWorkHistory(previousEnvelope, douyin, capturedAt) {
  const merged = new Map();
  for (const row of previousEnvelope?.history?.workSnapshots ?? []) {
    merged.set(historyKey(row), row);
  }
  for (const work of previousEnvelope?.douyin?.works ?? []) {
    for (const row of work.history ?? []) {
      const normalized = {
        ...row,
        publishedAt: work.publishedAt ?? null,
        title: work.title ?? null,
        platformWorkId: work.platformWorkId ?? null,
        sourcePath: `${STORE_RELATIVE}/work-history.csv`,
      };
      merged.set(historyKey(normalized), normalized);
    }
  }
  for (const work of douyin.works ?? []) {
    for (const row of work.history ?? []) {
      const normalized = {
        ...row,
        publishedAt: work.publishedAt ?? null,
        title: work.title ?? null,
        platformWorkId: work.platformWorkId ?? null,
        sourcePath: `${STORE_RELATIVE}/work-history.csv`,
      };
      merged.set(historyKey(normalized), normalized);
    }
  }
  for (const work of douyin.works ?? []) {
    const row = snapshotFromWork(work, capturedAt);
    merged.set(historyKey(row), row);
  }
  return [...merged.values()].sort((left, right) => {
    const time = String(left.capturedAt).localeCompare(String(right.capturedAt));
    if (time !== 0) return time;
    return workKey(left).localeCompare(workKey(right), "zh-CN");
  });
}

function mergeAccountHistory(previousEnvelope, latestRows) {
  const merged = new Map();
  for (const row of previousEnvelope?.history?.accountDaily ?? []) {
    if (row?.date) merged.set(row.date, row);
  }
  for (const row of latestRows ?? []) {
    if (row?.date) merged.set(row.date, row);
  }
  return [...merged.values()].sort((left, right) =>
    String(left.date).localeCompare(String(right.date)),
  );
}

function detailRowCount(detail) {
  return [
    detail.hourlyViews,
    detail.hourlyFollowerGain,
    detail.dailyFollowerCumulative,
    detail.progress,
    detail.retention,
    detail.bounce,
    detail.trafficSources,
    detail.pageEvidence?.chapters,
    detail.pageEvidence?.incomingSearchTerms,
    detail.pageEvidence?.postWatchSearchTerms,
    detail.pageEvidence?.geography,
    detail.pageEvidence?.interests,
    detail.pageEvidence?.audienceHotWords,
    detail.pageEvidence?.commentKeywords,
  ].reduce((sum, rows) => sum + (rows?.length ?? 0), 0);
}

function detailFields(detail) {
  const fields = new Set(Object.keys(detail.metrics ?? {}));
  for (const [key, rows] of Object.entries({
    hourlyViews: detail.hourlyViews,
    hourlyFollowerGain: detail.hourlyFollowerGain,
    dailyFollowerCumulative: detail.dailyFollowerCumulative,
    progress: detail.progress,
    retention: detail.retention,
    bounce: detail.bounce,
    trafficSources: detail.trafficSources,
    ...(detail.pageEvidence ?? {}),
  })) {
    if (Array.isArray(rows) && rows.length) fields.add(key);
  }
  return fields;
}

function mergeWorkDetails(previousEnvelope, douyin) {
  const previousWorks = new Map(
    (previousEnvelope?.douyin?.works ?? []).map((work) => [work.id, work]),
  );
  const currentWorks = new Map((douyin.works ?? []).map((work) => [work.id, work]));
  const byIdentity = new Map();

  for (const [id, detail] of Object.entries(
    previousEnvelope?.douyin?.analytics?.workDetails ?? {},
  )) {
    const work = previousWorks.get(id);
    if (work) byIdentity.set(workKey(work), detail);
  }
  for (const [id, detail] of Object.entries(douyin.analytics?.workDetails ?? {})) {
    const work = currentWorks.get(id);
    if (work) byIdentity.set(workKey(work), detail);
  }

  const result = {};
  for (const work of douyin.works ?? []) {
    const detail = byIdentity.get(workKey(work));
    if (!detail) continue;
    result[work.id] = {
      ...detail,
      workId: work.id,
      platformWorkId: work.platformWorkId ?? detail.platformWorkId ?? null,
      sourceKind: "normalized-local-store",
      sourcePaths: [`${STORE_RELATIVE}/work-details.json`],
    };
  }
  return result;
}

function applyStablePaths(douyin, history, accountHistory, workDetails) {
  douyin.sourcePath = `${STORE_RELATIVE}/works.csv`;
  for (const work of douyin.works ?? []) {
    const previousPlatformId = work.platformWorkId;
    const rows = history.filter((row) => workKey(row) === workKey(work));
    if (!previousPlatformId) {
      work.platformWorkId = rows.find((row) => row.platformWorkId)?.platformWorkId ?? null;
    }
    work.history = rows.map((row) => ({
      capturedAt: row.capturedAt,
      sourcePath: `${STORE_RELATIVE}/work-history.csv`,
      grain: row.grain,
      views: row.views,
      likes: row.likes,
      shares: row.shares,
      comments: row.comments,
      saves: row.saves,
      profileVisits: row.profileVisits,
      followerGain: row.followerGain,
    }));
  }

  const analytics = douyin.analytics;
  if (!analytics) return;
  analytics.snapshot = {
    rootPath: STORE_RELATIVE,
    capturedAt: douyin.updatedAt,
    timezone: "Asia/Shanghai",
    isRealtime: false,
    snapshotCount: new Set(history.map((row) => row.capturedAt)).size,
  };
  analytics.account.daily = analytics.account.daily ?? [];
  analytics.account.sourcePaths = [
    `${STORE_RELATIVE}/account-daily.csv`,
    `${STORE_RELATIVE}/current.json`,
  ];
  if (analytics.account.homeSnapshot) {
    analytics.account.homeSnapshot.sourcePath = `${STORE_RELATIVE}/current.json`;
  }
  analytics.collections = analytics.collections ?? [];
  analytics.workDetails = workDetails;

  const details = Object.values(workDetails);
  const fields = new Set();
  let pageOnlyRows = 0;
  for (const detail of details) {
    for (const field of detailFields(detail)) fields.add(field);
    pageOnlyRows += [
      detail.pageEvidence?.chapters,
      detail.pageEvidence?.incomingSearchTerms,
      detail.pageEvidence?.postWatchSearchTerms,
      detail.pageEvidence?.geography,
      detail.pageEvidence?.interests,
      detail.pageEvidence?.audienceHotWords,
      detail.pageEvidence?.commentKeywords,
    ].reduce((sum, rows) => sum + (rows?.length ?? 0), 0);
  }
  analytics.coverage.deepWorkCount = details.length;
  analytics.coverage.totalWorkCount = douyin.works.length;
  analytics.coverage.historyCoveredWorks = douyin.works.filter(
    (work) => (work.history?.length ?? 0) >= 2,
  ).length;
  analytics.coverage.accountDailyRows = analytics.account.daily.length;
  analytics.coverage.pageOnlyRows = pageOnlyRows;
  analytics.coverage.deepFieldCount = fields.size;

  const assetPaths = {
    "account-content-daily": `${STORE_RELATIVE}/account-daily.csv`,
    "account-follower-daily": `${STORE_RELATIVE}/account-daily.csv`,
    "all-works": `${STORE_RELATIVE}/works.csv`,
    "content-analysis": `${STORE_RELATIVE}/current.json`,
    collections: `${STORE_RELATIVE}/collections.csv`,
    "deep-work": `${STORE_RELATIVE}/work-details.json`,
    "page-evidence": `${STORE_RELATIVE}/work-details.json`,
  };
  for (const asset of analytics.coverage.assets ?? []) {
    asset.sourcePath = assetPaths[asset.id] ?? `${STORE_RELATIVE}/current.json`;
    if (asset.id === "deep-work") {
      asset.rowCount = details.reduce((sum, detail) => sum + detailRowCount(detail), 0);
      asset.fieldCount = fields.size;
      asset.grain = `已采集 ${details.length} / ${douyin.works.length} 条作品`;
      asset.status = details.length ? "partial" : "missing";
    }
    if (asset.id === "page-evidence") {
      asset.rowCount = pageOnlyRows;
      asset.status = pageOnlyRows ? "partial" : "missing";
    }
  }

  const partialIssue = (douyin.qualityIssues ?? []).find((item) =>
    String(item.issue).includes("单作品深度数据"),
  );
  if (partialIssue) {
    partialIssue.affectedWorks = `${details.length} / ${douyin.works.length} 条有深度采集`;
  }

  // Long history is stored beside, while the dashboard retains the current official window.
  void accountHistory;
}

async function manifestSummary(snapshotRoot) {
  if (!snapshotRoot) return null;
  const candidates = [
    path.join(snapshotRoot, "00_exports", "run_manifest.json"),
    path.join(snapshotRoot, "run_manifest.json"),
  ];
  for (const candidate of candidates) {
    try {
      const manifest = JSON.parse(await fs.readFile(candidate, "utf8"));
      return {
        schemaVersion: manifest.schemaVersion ?? 1,
        browserEngine: manifest.browserEngine ?? null,
        taskSpaceId: manifest.taskSpaceId ?? null,
        result: manifest.result ?? null,
        startedAt: manifest.startedAt ?? null,
        completedAt: manifest.completedAt ?? null,
        sourceUrl: manifest.sourceUrl ?? null,
        successCount: manifest.successCount ?? null,
        failureCount: manifest.failureCount ?? null,
        files: (manifest.files ?? []).map((file) => ({
          name: file.name ?? path.basename(file.path ?? ""),
          bytes: file.bytes ?? null,
          sha256: file.sha256 ?? null,
        })),
        failures: manifest.failures ?? [],
      };
    } catch {
      // Continue to the legacy location.
    }
  }
  return null;
}

async function payloadFromSnapshot(buildVaultIndex, vaultRoot, snapshotRoot) {
  const tempVault = await fs.mkdtemp(path.join(os.tmpdir(), "douyin-store-vault-"));
  try {
    const manifest = await manifestSummary(snapshotRoot);
    const stamp = String(manifest?.completedAt ?? new Date().toISOString())
      .replace(/[-:TZ.]/g, "")
      .slice(0, 14);
    const name = `${stamp.slice(0, 8)}-${stamp.slice(8, 14)}-creator-collector`;
    const target = path.join(tempVault, "10_raw", "douyin", name);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.cp(snapshotRoot, target, { recursive: true });
    const index = await buildVaultIndex(tempVault);
    ensure(index.douyin?.available, "临时快照无法生成 Workbench 抖音数据");
    return { douyin: index.douyin, snapshotRoot, manifest };
  } finally {
    await fs.rm(tempVault, { recursive: true, force: true });
  }
}

async function payloadFromCurrentVault(buildVaultIndex, vaultRoot) {
  const index = await buildVaultIndex(vaultRoot);
  ensure(index.douyin?.available, "当前 Vault 没有可迁移的 Workbench 抖音数据");
  const relative = index.douyin.analytics?.snapshot?.rootPath;
  const snapshotRoot = relative ? path.join(vaultRoot, relative) : null;
  return {
    douyin: index.douyin,
    snapshotRoot,
    manifest: await manifestSummary(snapshotRoot),
  };
}

async function readJsonIfPresent(filePath) {
  if (!filePath) return null;
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch {
    return null;
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function readmeText() {
  return `---
type: self-media-platform-data
status: active
platform: douyin
updated: ${new Date().toISOString().slice(0, 10)}
---

# 抖音固定数据仓库

本目录是自有抖音账号的长期数据层，也是 Workbench 抖音模块的唯一运行时来源。

## 固定文件

- \`current.json\`：Workbench 完整读取模型、当前口径、数据质量和来源摘要。
- \`account-daily.csv\`：账号与粉丝自然日历史，按日期更新。
- \`works.csv\`：全量作品当前累计指标，整表覆盖。
- \`work-history.csv\`：作品历次累计快照，按“采集时间 + 作品身份”幂等合并。
- \`work-details.json\`：单作品小时趋势、留存、流量、搜索词、地域、兴趣和热词。
- \`collections.csv\`：当前合集数据。
- \`analysis.json\`：本轮数据质量与可审计事实，固定覆盖。
- \`last-run.json\`：最近一次运行状态，不创建日期化日志。

## 更新边界

采集器只在系统临时目录下载 Excel、CSV 和页面 JSON。质量通过后，本目录整套原子替换；失败时保留上一版有效数据。临时目录在每轮结束时删除，不进入 \`10_raw/douyin/\`。
`;
}

async function writeStore({
  vaultRoot,
  outputRoot,
  previousEnvelope,
  source,
  analysisPath,
}) {
  const analysis = ensure(await readJsonIfPresent(analysisPath), "缺少有效 analysis.json");
  ensure(
    analysis.data_quality?.status !== "failed",
    "数据质量失败，拒绝更新固定数据仓库",
  );
  const douyin = clone(source.douyin);
  const capturedAt =
    source.manifest?.completedAt ?? analysis.generated_at ?? douyin.updatedAt;
  douyin.updatedAt = capturedAt;

  const classifications = new Map(
    (analysis.work_classifications ?? []).map((item) => [
      workKey({ publishedAt: item.published_at, title: item.title }),
      item,
    ]),
  );
  for (const work of douyin.works ?? []) {
    const item = classifications.get(workKey(work));
    work.contentLine = work.contentLine ?? item?.content_line ?? "未分类";
    work.contentRole = work.contentRole ?? item?.content_role ?? "未分类";
  }

  const previousByIdentity = new Map(
    (previousEnvelope?.douyin?.works ?? []).map((work) => [workKey(work), work]),
  );
  for (const work of douyin.works ?? []) {
    const previous = previousByIdentity.get(workKey(work));
    if (!work.platformWorkId && previous?.platformWorkId) {
      work.platformWorkId = previous.platformWorkId;
    }
  }

  const accountHistory = mergeAccountHistory(
    previousEnvelope,
    douyin.analytics?.account?.daily ?? [],
  );
  const history = mergeWorkHistory(previousEnvelope, douyin, capturedAt);
  const workDetails = mergeWorkDetails(previousEnvelope, douyin);
  applyStablePaths(douyin, history, accountHistory, workDetails);

  const envelope = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    capturedAt,
    timezone: "Asia/Shanghai",
    dataQuality: analysis.data_quality,
    source: {
      platform: "douyin-creator-center",
      temporarySourcesDeleted: true,
      manifest: source.manifest,
    },
    files: Object.fromEntries(
      REQUIRED_FILES.map((name) => [name.replace(/[.-]/g, "_"), `${STORE_RELATIVE}/${name}`]),
    ),
    history: {
      accountDaily: accountHistory,
      workSnapshots: history,
    },
    douyin,
  };

  await fs.mkdir(outputRoot, { recursive: true });
  await fs.writeFile(path.join(outputRoot, "README.md"), readmeText(), "utf8");
  await fs.writeFile(
    path.join(outputRoot, "current.json"),
    `${JSON.stringify(envelope, null, 2)}\n`,
    "utf8",
  );

  const accountHeaders = [
    "日期",
    "投稿量",
    "总播放量",
    "总点赞量",
    "总评论量",
    "5秒完播率",
    "2秒跳出率",
    "封面点击率",
    "平均播放时长",
    "总粉丝量",
    "粉丝净增",
    "吸粉量",
    "脱粉量",
    "回访粉丝量",
  ];
  await fs.writeFile(
    path.join(outputRoot, "account-daily.csv"),
    csvText(
      accountHeaders,
      accountHistory.map((row) => [
        row.date,
        row.posts,
        row.views,
        row.likes,
        row.comments,
        row.fiveSecondCompletionRatePct,
        row.twoSecondBounceRatePct,
        row.coverClickRatePct,
        row.averageWatchSeconds,
        row.totalFollowers,
        row.netFollowerGain,
        row.followersGained,
        row.followersLost,
        row.returningFollowers,
      ]),
    ),
    "utf8",
  );

  const workHeaders = [
    "发布时间",
    "作品名称",
    "体裁",
    "审核状态",
    "播放量",
    "完播率",
    "5s完播率",
    "封面点击率",
    "2s跳出率",
    "平均播放时长",
    "点赞量",
    "分享量",
    "评论量",
    "收藏量",
    "主页访问量",
    "粉丝增量",
    "内容线",
    "内容角色",
    "平台作品ID",
  ];
  await fs.writeFile(
    path.join(outputRoot, "works.csv"),
    csvText(
      workHeaders,
      (douyin.works ?? []).map((work) => [
        work.publishedAt,
        work.title,
        work.format,
        work.reviewStatus,
        work.views,
        pctDecimal(work.completionRatePct),
        pctDecimal(work.fiveSecondCompletionRatePct),
        pctDecimal(work.coverClickRatePct),
        pctDecimal(work.twoSecondBounceRatePct),
        work.averageWatchSeconds,
        work.likes,
        work.shares,
        work.comments,
        work.saves,
        work.profileVisits,
        work.followerGain,
        work.contentLine,
        work.contentRole,
        work.platformWorkId,
      ]),
    ),
    "utf8",
  );

  const historyHeaders = [
    "采集时间",
    "发布时间",
    "作品名称",
    "平台作品ID",
    "播放量",
    "点赞量",
    "分享量",
    "评论量",
    "收藏量",
    "主页访问量",
    "粉丝增量",
  ];
  await fs.writeFile(
    path.join(outputRoot, "work-history.csv"),
    csvText(
      historyHeaders,
      history.map((row) => [
        row.capturedAt,
        row.publishedAt,
        row.title,
        row.platformWorkId,
        row.views,
        row.likes,
        row.shares,
        row.comments,
        row.saves,
        row.profileVisits,
        row.followerGain,
      ]),
    ),
    "utf8",
  );

  await fs.writeFile(
    path.join(outputRoot, "work-details.json"),
    `${JSON.stringify(
      { schemaVersion: 1, capturedAt, works: workDetails },
      null,
      2,
    )}\n`,
    "utf8",
  );
  const collectionHeaders = [
    "合集名称",
    "发布时间",
    "审核状态",
    "播放量",
    "完播率",
    "封面点击率",
    "2s跳出率",
    "平均播放时长",
    "点赞量",
    "分享量",
    "评论量",
    "收藏量",
    "粉丝增量",
  ];
  await fs.writeFile(
    path.join(outputRoot, "collections.csv"),
    csvText(
      collectionHeaders,
      (douyin.analytics?.collections ?? []).map((item) => [
        item.name,
        item.publishedAt,
        item.reviewStatus,
        item.views,
        pctDecimal(item.completionRatePct),
        pctDecimal(item.coverClickRatePct),
        pctDecimal(item.twoSecondBounceRatePct),
        item.averageWatchSeconds,
        item.likes,
        item.shares,
        item.comments,
        item.saves,
        item.followerGain,
      ]),
    ),
    "utf8",
  );
  await fs.copyFile(analysisPath, path.join(outputRoot, "analysis.json"));
  await fs.writeFile(
    path.join(outputRoot, "last-run.json"),
    `${JSON.stringify(
      {
        schemaVersion: 1,
        status: "complete",
        completedAt: new Date().toISOString(),
        capturedAt,
        dataQuality: analysis.data_quality.status,
        temporarySourcesDeleted: true,
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  await verifyStore(outputRoot);
  return envelope;
}

async function verifyStore(root) {
  for (const name of REQUIRED_FILES) {
    const value = await fs.stat(path.join(root, name));
    ensure(value.isFile() && value.size > 0, `固定数据文件缺失或为空：${name}`);
  }
  const envelope = JSON.parse(await fs.readFile(path.join(root, "current.json"), "utf8"));
  ensure(envelope.schemaVersion === 1, "current.json schemaVersion 不正确");
  ensure(envelope.dataQuality?.status !== "failed", "current.json 数据质量失败");
  ensure(envelope.douyin?.available === true, "current.json 没有可用抖音数据");
  ensure(
    envelope.douyin.sourcePath === `${STORE_RELATIVE}/works.csv`,
    "Workbench 作品来源没有切换到固定文件",
  );
  const works = envelope.douyin.works ?? [];
  const totalViews = works.reduce((sum, work) => sum + (work.views ?? 0), 0);
  ensure(
    totalViews === envelope.douyin.summary?.totalViews,
    "作品播放汇总与 current.json summary 不一致",
  );
  const serialized = JSON.stringify(envelope.douyin);
  ensure(!serialized.includes("creator-collector"), "固定数据仍引用临时采集目录");
  return envelope;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const vaultRoot = path.resolve(ensure(args.vault, "必须提供 --vault"));
  if (args["failure-status"]) {
    const root = path.resolve(ensure(args.output, "记录失败必须提供 --output"));
    await fs.mkdir(root, { recursive: true });
    await fs.writeFile(
      path.join(root, "last-run.json"),
      `${JSON.stringify(
        {
          schemaVersion: 1,
          status: args["failure-status"],
          completedAt: new Date().toISOString(),
          message: args["failure-message"] ?? null,
          temporarySourcesDeleted: true,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
    console.log(JSON.stringify({ ok: true, status: args["failure-status"] }));
    return;
  }
  if (args.verify) {
    const root = path.resolve(ensure(args.output, "verify 必须提供 --output"));
    const envelope = await verifyStore(root);
    console.log(
      JSON.stringify(
        {
          ok: true,
          capturedAt: envelope.capturedAt,
          works: envelope.douyin.works.length,
          totalViews: envelope.douyin.summary.totalViews,
        },
        null,
        2,
      ),
    );
    return;
  }

  const workbenchRoot = path.resolve(
    ensure(
      args["workbench-root"] ?? process.env.PERSONAL_DASHBOARD_WORKBENCH_ROOT,
      "必须提供 --workbench-root 或 PERSONAL_DASHBOARD_WORKBENCH_ROOT",
    ),
  );
  const vaultIndexPath = path.join(workbenchRoot, "server", "vault-index.mjs");
  const vaultIndexModule = await import(pathToFileURL(vaultIndexPath).href);
  const buildVaultIndex = ensure(
    vaultIndexModule.buildVaultIndex,
    "Workbench 未导出 buildVaultIndex",
  );

  const outputRoot = path.resolve(ensure(args.output, "必须提供 --output"));
  const source = args.bootstrap
    ? await payloadFromCurrentVault(buildVaultIndex, vaultRoot)
    : await payloadFromSnapshot(
        buildVaultIndex,
        vaultRoot,
        path.resolve(ensure(args.snapshot, "必须提供 --snapshot")),
      );
  const previousEnvelope = await readJsonIfPresent(args.existing);
  const envelope = await writeStore({
    vaultRoot,
    outputRoot,
    previousEnvelope,
    source,
    analysisPath: path.resolve(ensure(args.analysis, "必须提供 --analysis")),
  });
  console.log(
    JSON.stringify(
      {
        ok: true,
        output: outputRoot,
        capturedAt: envelope.capturedAt,
        works: envelope.douyin.works.length,
        totalViews: envelope.douyin.summary.totalViews,
        historyRows: envelope.history.workSnapshots.length,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
});
