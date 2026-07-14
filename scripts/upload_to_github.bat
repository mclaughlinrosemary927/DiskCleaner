@echo off
chcp 65001 >nul
title 一键上传到 GitHub

echo.
echo ============================================================
echo   一键上传 DiskCleaner 项目到 GitHub
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

:: 运行上传脚本
echo 正在上传...
python github_sync.py --backup

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   [成功] 上传完成！
    echo ============================================================
    echo.
    echo 仓库地址: https://github.com/mclaughlinrosemary927/DiskCleaner
    echo.
) else (
    echo.
    echo [错误] 上传失败，请检查网络连接或 GitHub 配置
)

pause
