@echo off
chcp 65001 >nul
title 一键从 GitHub 恢复

echo.
echo ============================================================
echo   一键从 GitHub 恢复完整环境
echo ============================================================
echo.

cd /d "%~dp0"

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.12+
    pause
    exit /b 1
)

:: 确认操作
echo 警告：此操作将覆盖本地的 OpenClaw 数据！
echo.
set /p confirm="确认要恢复吗？(输入 y 继续): "
if /i not "%confirm%"=="y" (
    echo 已取消操作
    pause
    exit /b 0
)

:: 运行恢复脚本
echo.
echo 正在恢复...
python github_sync.py --restore

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   [成功] 恢复完成！
    echo ============================================================
    echo.
    echo 重要提示：
    echo 1. 请重启 OpenClaw 以加载对话历史
    echo 2. 所有对话和上下文将自动恢复
    echo.
) else (
    echo.
    echo [错误] 恢复失败，请检查网络连接或 GitHub 配置
)

pause
