# lu-skills

个人 skills 备份仓库。仓库当前为公开状态，请勿提交真实 API key、访问令牌、个人数据或其他不适合公开的信息。

## 内容

- 根目录中原有技能文件夹：保留已有的 WorkBuddy 技能备份，本次同步未删除或覆盖。
- [`codex-skills/`](./codex-skills/)：2026-09-29 从 Codex 用户级技能目录整理的 68 个顶层文件夹、74 个 `SKILL.md` manifest，附完整名单与安装说明。

## 恢复 Codex skills

将 `codex-skills/` 下的技能文件夹复制到 `%USERPROFILE%\.agents\skills\` 或 `%USERPROFILE%\.codex\skills\`。详细步骤见 [codex-skills/README.md](./codex-skills/README.md)。

已清理两处安装目录间完全相同的副本、Python 缓存、旧备份和评测夹具。原有 WorkBuddy 技能备份保留；若技能仅名称相同但实现不同，则分开保存在原有目录和 `codex-skills/` 中。