@echo off
REM WorkBuddy 技能安装器 —— 双击本文件即可运行(无需打开 Git Bash)
REM 如需自定义参数，例如自动重启，可在下方末尾追加 -Restart
powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0install-skills.ps1" %*
