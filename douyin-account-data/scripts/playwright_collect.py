#!/usr/bin/env python3
"""Collect official Douyin Creator Center exports through the visible UI.

This browser adapter intentionally uses a dedicated Playwright profile and the
platform's own export buttons. It does not inspect cookies, intercept responses,
or call private endpoints.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Sequence


HOME_URL = "https://creator.douyin.com/creator-micro/home"
OPERATION_URL = "https://creator.douyin.com/creator-micro/data-center/operation"
CONTENT_URL = "https://creator.douyin.com/creator-micro/data-center/content"
WORK_LIST_URL = "https://creator.douyin.com/creator-micro/content/manage?enter_from=publish"
LOGIN_MARKERS = re.compile(r"账号总览|作品分析|粉丝分析|内容管理|数据中心")
LOGIN_BLOCKERS = re.compile(r"扫码登录|登录后即可|登录/注册|登录 / 注册")
CHALLENGE_MARKERS = re.compile(r"验证码|安全验证|完成验证|访问过于频繁|操作频繁|账号确认")
WORK_ID_PATTERN = re.compile(r"work-detail/(\d+)")
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]


class CollectorError(RuntimeError):
    pass


class AuthRequired(CollectorError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", value or "download.bin")
    cleaned = normalize_text(cleaned)
    return cleaned or "download.bin"


def unique_path(directory: Path, name: str) -> Path:
    candidate = directory / safe_filename(name)
    index = 2
    while candidate.exists():
        candidate = directory / f"{candidate.stem}-{index}{candidate.suffix}"
        index += 1
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_work_ids(value: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    if any(not item.isdigit() for item in values):
        raise argparse.ArgumentTypeError("work IDs must be comma-separated numeric values")
    return list(dict.fromkeys(values))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use Playwright to download official exports from an authorized Douyin account."
    )
    parser.add_argument("mode", choices=("check", "probe", "collect-weekly"))
    parser.add_argument("--profile-dir", type=Path, required=True)
    parser.add_argument(
        "--browser-channel", choices=("chromium", "chrome", "msedge"), default="chromium"
    )
    parser.add_argument("--login-timeout", type=int, default=300)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--snapshot-dir", type=Path)
    parser.add_argument("--work-ids", type=parse_work_ids, default=[])
    args = parser.parse_args(argv)
    if args.login_timeout < 30:
        parser.error("--login-timeout must be at least 30 seconds")
    if args.mode == "collect-weekly" and (not args.output_dir or not args.snapshot_dir):
        parser.error("collect-weekly requires --output-dir and --snapshot-dir")
    return args


@dataclass
class RunState:
    output_dir: Path
    snapshot_dir: Path
    results: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[str] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    work_ids: list[str] = field(default_factory=list)
    next_sequence: int = 1


async def launch_context(playwright: Any, profile_dir: Path, channel: str) -> Any:
    options: dict[str, Any] = {
        "user_data_dir": str(profile_dir),
        "headless": False,
        "accept_downloads": True,
        "viewport": {"width": 1440, "height": 1000},
    }
    if channel != "chromium":
        options["channel"] = channel
    return await playwright.chromium.launch_persistent_context(**options)


async def body_text(page: Any) -> str:
    return await page.locator("body").inner_text(timeout=30_000)


async def login_state(page: Any) -> dict[str, Any]:
    text = await body_text(page)
    url = page.url
    challenge = bool(CHALLENGE_MARKERS.search(text))
    return {
        "ok": (
            "creator.douyin.com/creator-micro/" in url
            and "/login" not in url
            and bool(LOGIN_MARKERS.search(text))
            and not bool(LOGIN_BLOCKERS.search(text))
            and not challenge
        ),
        "challenge": challenge,
        "title": await page.title(),
        "url": url,
    }


async def wait_for_login(
    page: Any, timeout_seconds: int, *, allow_interactive_challenge: bool = False
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        try:
            state = await login_state(page)
        except Exception:
            state = {"ok": False, "challenge": False, "title": "", "url": page.url}
        if state["ok"]:
            return state
        if state.get("challenge") and not allow_interactive_challenge:
            raise AuthRequired("检测到安全验证，请在浏览器中处理后重新运行")
        if asyncio.get_running_loop().time() >= deadline:
            reason = "安全验证未完成" if state.get("challenge") else "登录未完成"
            raise AuthRequired(f"{reason}，请在已打开的浏览器中处理后重试")
        await asyncio.sleep(1)


async def goto_ready(page: Any, url: str, login_timeout: int) -> None:
    await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    await page.wait_for_timeout(1_500)
    await wait_for_login(page, min(login_timeout, 60))


async def visible_matches(locator: Any, text: str, exact: bool) -> list[Any]:
    matches: list[Any] = []
    for index in range(await locator.count()):
        item = locator.nth(index)
        if not await item.is_visible():
            continue
        value = normalize_text(await item.inner_text())
        if value == text if exact else text in value:
            matches.append(item)
    return matches


async def wait_for_matches(
    locator: Any, text: str, count: int, exact: bool = False, timeout_seconds: int = 30
) -> list[Any]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    matches = await visible_matches(locator, text, exact)
    while len(matches) != count and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.5)
        matches = await visible_matches(locator, text, exact)
    if len(matches) != count:
        raise CollectorError(f'控件“{text}”预期 {count} 个，实际为 {len(matches)} 个')
    return matches


async def click_role_exact(page: Any, role: str, label: str) -> None:
    items = await wait_for_matches(page.locator(f'[role="{role}"]'), label, 1, exact=True)
    await items[0].click()
    await page.wait_for_timeout(700)


async def click_radio_label(
    page: Any, label: str, index: int = 0, expected_count: int = 1
) -> None:
    radios = page.locator('input[type="radio"]')
    matches: list[Any] = []
    for position in range(await radios.count()):
        radio = radios.nth(position)
        parent = radio.locator("xpath=../..")
        if normalize_text(await parent.inner_text()) == label:
            matches.append(parent)
    if len(matches) != expected_count or index >= len(matches):
        raise CollectorError(
            f'单选项“{label}”预期 {expected_count} 个，实际为 {len(matches)} 个'
        )
    await matches[index].click()
    await page.wait_for_timeout(700)


async def capture_snapshot(page: Any, state: RunState, label: str) -> Path:
    payload = {
        "schemaVersion": 1,
        "capturedAt": iso(),
        "label": label,
        "title": await page.title(),
        "url": page.url,
        "bodyText": (await body_text(page)).strip(),
    }
    target = unique_path(state.snapshot_dir, f"{safe_filename(label)}.json")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state.snapshots.append(str(target))
    return target


async def download_button(
    page: Any,
    state: RunState,
    *,
    text: str,
    exact: bool,
    index: int,
    label: str,
) -> dict[str, Any]:
    matches = await visible_matches(page.locator("button"), text, exact)
    if index >= len(matches):
        raise CollectorError(f'下载按钮“{text}”索引 {index} 不存在，当前共 {len(matches)} 个')

    started_at = utc_now()
    started_clock = asyncio.get_running_loop().time()
    async with page.expect_download(timeout=120_000) as download_info:
        await matches[index].click()
    download = await download_info.value
    suggested = safe_filename(download.suggested_filename or "export.xlsx")
    target = unique_path(
        state.output_dir,
        f"{state.next_sequence:02d}-{safe_filename(label)}__{suggested}",
    )
    state.next_sequence += 1
    await download.save_as(str(target))
    if not target.is_file() or target.stat().st_size == 0:
        raise CollectorError(f"下载文件为空：{label}")

    record = {
        "ok": True,
        "label": label,
        "startedAt": iso(started_at),
        "capturedAt": iso(),
        "elapsedMs": round((asyncio.get_running_loop().time() - started_clock) * 1000),
        "source": {
            "title": await page.title(),
            "url": page.url,
            "browserEngine": "playwright",
        },
        "file": {
            "name": target.name,
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        },
        "requestTrace": [],
    }
    Path(f"{target}.manifest.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    state.results.append(record)
    return record


async def collect_visible_exports(
    page: Any,
    state: RunState,
    labels: Sequence[str],
    *,
    text: str = "导出数据",
    exact: bool = False,
) -> None:
    await wait_for_matches(page.locator("button"), text, len(labels), exact)
    for index, label in enumerate(labels):
        await download_button(
            page, state, text=text, exact=exact, index=index, label=label
        )


async def discover_work_ids(page: Any) -> list[str]:
    ids: list[str] = []
    anchors = page.locator('a[href*="/work-management/work-detail/"]')
    for index in range(await anchors.count()):
        href = await anchors.nth(index).get_attribute("href") or ""
        match = WORK_ID_PATTERN.search(href)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    if ids:
        return ids

    links = await visible_matches(page.locator("a,button"), "查看分析", exact=True)
    if len(links) == 1:
        await links[0].click()
        try:
            await page.wait_for_url(re.compile(r".*/work-detail/\d+.*"), timeout=30_000)
        except Exception:
            return ids
        match = WORK_ID_PATTERN.search(page.url)
        if match:
            ids.append(match.group(1))
    return ids


async def run_step(state: RunState, name: str, operation: Callable[[], Awaitable[None]]) -> None:
    try:
        await operation()
    except AuthRequired:
        raise
    except Exception as error:
        state.failures.append({"step": name, "error": str(error)})


async def collect_weekly(page: Any, args: argparse.Namespace) -> int:
    output_dir = args.output_dir.resolve()
    snapshot_dir = args.snapshot_dir.resolve()
    system_temp = Path(tempfile.gettempdir()).resolve()
    if not is_within(output_dir, system_temp) or not is_within(snapshot_dir, system_temp):
        raise CollectorError("采集输出与页面证据必须位于系统临时目录")
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    state = RunState(
        output_dir=output_dir,
        snapshot_dir=snapshot_dir,
        work_ids=list(args.work_ids),
    )
    started_at = utc_now()

    await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=120_000)
    print("已打开抖音创作者中心；首次运行请在浏览器窗口中完成扫码或验证。", flush=True)
    await wait_for_login(page, args.login_timeout, allow_interactive_challenge=True)

    async def home_step() -> None:
        await goto_ready(page, HOME_URL, args.login_timeout)
        await capture_snapshot(page, state, "首页-当前")
        state.work_ids = list(dict.fromkeys([*state.work_ids, *await discover_work_ids(page)]))
        if not state.work_ids:
            raise CollectorError("首页未发现可用作品详情链接，且未提供 --work-ids")

    async def account_step() -> None:
        await goto_ready(page, OPERATION_URL, args.login_timeout)
        await wait_for_matches(page.locator("button"), "导出数据", 2)
        for ui_label, file_label in (("昨天", "昨日"), ("近7天", "近7天"), ("近30天", "近30天")):
            await click_radio_label(page, ui_label, 0, 2)
            await download_button(
                page,
                state,
                text="导出数据",
                exact=False,
                index=0,
                label=f"{file_label}-作品数据表现",
            )
            await click_radio_label(page, ui_label, 1, 2)
            await download_button(
                page,
                state,
                text="导出数据",
                exact=False,
                index=1,
                label=f"{file_label}-粉丝数据表现",
            )

    async def content_step() -> None:
        await goto_ready(page, CONTENT_URL, args.login_timeout)
        await click_role_exact(page, "tab", "投稿作品")
        await click_radio_label(page, "投稿分析")
        await collect_visible_exports(page, state, ["投稿概览", "投稿表现"])
        await click_radio_label(page, "投稿列表")
        await collect_visible_exports(page, state, ["投稿列表"])
        await click_role_exact(page, "tab", "合集")
        await click_radio_label(page, "合集分析")
        await collect_visible_exports(page, state, ["合集概览", "合集表现"])
        await click_radio_label(page, "合集列表")
        await collect_visible_exports(page, state, ["合集列表"])

    async def work_list_step() -> None:
        await goto_ready(page, WORK_LIST_URL, args.login_timeout)
        await collect_visible_exports(page, state, ["作品列表"])

    await run_step(state, "首页快照与作品发现", home_step)
    await run_step(state, "账号数据总览", account_step)
    await run_step(state, "投稿与合集", content_step)
    await run_step(state, "作品列表", work_list_step)

    for work_id in state.work_ids:
        async def work_step(current_work_id: str = work_id) -> None:
            url = (
                "https://creator.douyin.com/creator-micro/work-management/work-detail/"
                f"{current_work_id}?enter_from=homepage"
            )
            await goto_ready(page, url, args.login_timeout)
            plans = (
                ("总览", ("总览-流量数据", "总览-粉丝数据")),
                ("流量分析", ("流量分析-内容吸引力", "流量分析-观众参与度", "流量分析-流量来源")),
                ("观众分析", ("观众分析-观众数据",)),
            )
            for tab, labels in plans:
                await click_role_exact(page, "tab", tab)
                await capture_snapshot(page, state, f"作品-{current_work_id}-{tab}")
                await collect_visible_exports(
                    page,
                    state,
                    [f"{current_work_id}-{label}" for label in labels],
                    text="导出",
                    exact=True,
                )
            try:
                await click_role_exact(page, "tab", "评论热词")
                await capture_snapshot(page, state, f"作品-{current_work_id}-评论热词")
            except Exception:
                pass

        await run_step(state, f"作品详情 {work_id}", work_step)

    completed_at = utc_now()
    result = "complete" if not state.failures else "partial" if state.results else "failed"
    manifest = {
        "schemaVersion": 1,
        "mode": "weekly",
        "startedAt": iso(started_at),
        "completedAt": iso(completed_at),
        "elapsedMs": round((completed_at - started_at).total_seconds() * 1000),
        "sourceUrl": CONTENT_URL,
        "browserEngine": "playwright",
        "profileDir": "dedicated local Playwright profile",
        "result": result,
        "successCount": len(state.results),
        "failureCount": len(state.failures),
        "workIds": state.work_ids,
        "files": [item["file"] for item in state.results],
        "pageSnapshots": state.snapshots,
        "failures": state.failures,
    }
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": not state.failures,
                "result": result,
                "successCount": len(state.results),
                "failureCount": len(state.failures),
                "workCount": len(state.work_ids),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not state.failures else 3


async def async_main(args: argparse.Namespace) -> int:
    # Import lazily so validation and unit tests can run before Playwright is installed.
    from playwright.async_api import async_playwright

    args.profile_dir = args.profile_dir.expanduser().resolve()
    if is_within(args.profile_dir, REPO_ROOT):
        raise CollectorError("Playwright 登录目录不能位于公开 Skill 仓库内")
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await launch_context(playwright, args.profile_dir, args.browser_channel)
        try:
            if args.mode == "check":
                print(json.dumps({"ok": True, "browserEngine": "playwright", "channel": args.browser_channel}))
                return 0
            page = context.pages[0] if context.pages else await context.new_page()
            if args.mode == "probe":
                await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=120_000)
                await wait_for_login(page, args.login_timeout, allow_interactive_challenge=True)
                print(json.dumps({"ok": True, "browserEngine": "playwright"}))
                return 0
            return await collect_weekly(page, args)
        finally:
            await context.close()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(parse_args(argv)))
    except AuthRequired as error:
        print(f"status=blocked_auth\nmessage={error}", file=sys.stderr)
        return 21
    except KeyboardInterrupt:
        print("status=cancelled", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"status=collector_failed\nmessage={error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
