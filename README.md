# workbuddy-skills

WorkBuddy 用户级技能仓库（自动备份镜像）。

## 说明
- 由本地每日自动化（11:00）自动维护：`git commit` + 打包 `tar.gz` + `git push`，**请勿手动编辑**，以免与本地提交产生冲突。
- 内容：用户级技能（`~/.workbuddy/skills`），含技能市场安装技能与自定义技能。
- 凭据（如 API token）已排除，不会进入本仓库；敏感文件由 `.gitignore` 及打包排除规则屏蔽。
- 本仓库为**私有**，仅供本人同步备份使用。

## 恢复
本仓库是本地 `~/.workbuddy/skills` 的镜像。如需恢复，克隆本仓库或拷贝其 `.git` 目录到本地对应位置即可。
