# GitHub 同步脚本使用说明

本目录包含 DiskCleaner 的备份与恢复工具。脚本会把项目文件和配置数据同步到 GitHub 仓库，适合在换电脑或重装环境时恢复。

## 使用前准备

1. 安装 Python 3.12 或更高版本。
2. 安装 Git，并确认 `git --version` 可以在终端运行。
3. 检查 `github_config.py` 中的仓库地址和用户名。
4. 确认 GitHub 仓库已经创建，并且当前 Git 凭据有推送权限。

## 上传到 GitHub

在项目根目录双击 `scripts\upload_to_github.bat`，或在 PowerShell 中运行：

```powershell
python scripts\github_sync.py --backup
```

上传脚本会创建或更新备份目录、提交变更，然后推送到 GitHub。首次使用时，如果仓库不存在，请先在 GitHub 创建目标仓库。

## 从 GitHub 拉取并恢复

在项目根目录双击 `scripts\download_from_github.bat`，或运行：

```powershell
python scripts\github_sync.py --restore
```

恢复操作会覆盖目标位置中同名的项目与 OpenClaw 数据。批处理文件会先要求输入 `y` 确认；执行前请关闭正在运行的相关程序，并确认仓库内容是你要恢复的版本。

恢复完成后，重启 OpenClaw，让对话历史和配置重新加载。

## 文件说明

- `github_sync.py`：实际执行备份、提交、推送和恢复的 Python 脚本。
- `upload_to_github.bat`：Windows 一键上传入口。
- `download_from_github.bat`：Windows 一键恢复入口。
- `build_exe.bat`：构建当前版本的 `dist\DiskCleaner.exe`。

## 构建 EXE

修改 `disk_cleaner_gui_v8.py` 后，在项目根目录双击 `scripts\build_exe.bat`，或运行：

```powershell
scripts\build_exe.bat
```

构建完成后，将使用最新源码生成 `dist\DiskCleaner.exe`。该程序是无控制台窗口的桌面应用，首次启动时仍会按原逻辑请求管理员权限。

## 夸克网盘设备盘

夸克网盘使用 `Q:` 作为 WebDAV 后端，并由 WinFsp 与 rclone 提供 `X:` 虚拟固定盘。资源管理器会将 `X:` 显示为卷名“夸克网盘”的设备驱动器。

- `mount_quark_device_drive.ps1`：登录后自动恢复 `X:` 挂载。
- `DiskCleaner-QuarkDeviceDrive`：当前用户的登录启动项，后台运行上述脚本。
- `rclone` 配置中的 `quark-webdav` 和 `quark-device`：分别对应本机 AList WebDAV 与夸克根目录。

需要重新挂载时，可在 DiskCleaner 的“云端同步”页面点击“重新挂载”。

脚本不会重新启用 AGENTS.md 中明确禁用的 Windows 自动备份任务，也不会创建已删除的 OpenClaw 自定义备份任务。
