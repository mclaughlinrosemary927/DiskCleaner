#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiskCleaner 项目 GitHub 同步工具
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT_DIR = SCRIPT_DIR.parent
if str(PROJECT_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIR))

# ========== 配置区 ==========
try:
    from github_config import GITHUB_REPO, GITHUB_USERNAME
except ImportError:
    GITHUB_REPO = "https://github.com/YOUR_USERNAME/diskcleaner-backup.git"
    GITHUB_USERNAME = "YOUR_USERNAME"

PROJECT_ROOT = Path(r"C:\Users\Administrator\.qclaw\workspace")
OPENCLAW_ROOT = Path(r"C:\Users\Administrator\.qclaw")
BACKUP_DIR = PROJECT_ROOT / ".github_backup"

OPENCLAW_DATA = [
    "lcm-files",
    "qmemory",
    "memory",
    "openclaw.json",
    "agents",
    "identity",
    # "skills",  # 跳过，文件名编码问题
    "tools",
    "canvas",
    "flows",
]

PROJECT_FILES = [
    "disk_cleaner_gui_v8.py",
    "app_icon.ico",
    "app_icon.png",
    "AGENTS.md",
    "MEMORY.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
    "IDENTITY.md",
    "memory",
]


def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def run_command(cmd, cwd=None, check=True):
    print(f"[执行] {cmd}")
    git_path = r"C:\Program Files\Git\bin\git.exe"
    if cmd.startswith("git "):
        cmd = f'"{git_path}" ' + cmd[4:]
    
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.stdout:
        print(result.stdout)
    if result.stderr and result.stderr.strip():
        print(f"[警告] {result.stderr}")
    
    if check and result.returncode != 0:
        print(f"[错误] 命令执行失败，返回码: {result.returncode}")
        sys.exit(1)
    
    return result


def create_gitignore():
    content = """# Python
__pycache__/
*.py[cod]
build/
dist/
*.egg-info/

# PyInstaller
*.spec
*.exe

# OpenClaw cache
.auto-memory/
browser/
logs/
node_modules/
*.db
*.log
*.tmp

# Temp
*.bak
.DS_Store
"""
    path = BACKUP_DIR / ".gitignore"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[创建] {path}")


def create_readme():
    content = f"""# DiskCleaner 项目完整备份

## 备份内容

- 项目代码: disk_cleaner_gui_v8.py
- OpenClaw 对话历史: lcm-files/
- 配置文件: openclaw.json, AGENTS.md, MEMORY.md

## 恢复方法

```bash
python github_sync.py --restore
```

备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    path = BACKUP_DIR / "README.md"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[创建] {path}")


def backup_project_files():
    print("\n[步骤 1] 备份项目文件...")
    for item in PROJECT_FILES:
        src = PROJECT_ROOT / item
        dst = BACKUP_DIR / item
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  [OK] {item}/")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  [OK] {item}")


def backup_openclaw_data():
    print("\n[步骤 2] 备份 OpenClaw 数据...")
    for item in OPENCLAW_DATA:
        src = OPENCLAW_ROOT / item
        dst = BACKUP_DIR / "openclaw_data" / item
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                file_count = sum(1 for _ in dst.rglob('*') if _.is_file())
                print(f"  [OK] {item}/ ({file_count} files)")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  [OK] {item}")


def copy_sync_script():
    print("\n[步骤 3] 复制同步脚本...")
    src = Path(__file__).absolute()
    dst = BACKUP_DIR / "github_sync.py"
    shutil.copy2(src, dst)
    print(f"  [OK] github_sync.py")


def init_git_repo():
    print("\n[步骤 4] 初始化 Git 仓库...")
    if (BACKUP_DIR / ".git").exists():
        print("  [OK] Git 仓库已存在")
        return
    run_command("git init", cwd=BACKUP_DIR)
    print("  [OK] Git 仓库初始化完成")


def commit_changes():
    print("\n[步骤 5] 提交更改...")
    run_command("git add -A", cwd=BACKUP_DIR)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    run_command(f'git commit -m "Backup: {timestamp}"', cwd=BACKUP_DIR)
    print(f"  [OK] 提交完成")


def push_to_github():
    print("\n[步骤 6] 推送到 GitHub...")
    result = run_command("git remote -v", cwd=BACKUP_DIR, check=False)
    if "origin" not in result.stdout:
        print(f"  -> 添加远程仓库: {GITHUB_REPO}")
        run_command(f"git remote add origin {GITHUB_REPO}", cwd=BACKUP_DIR)
    
    print("  -> 推送到 GitHub...")
    result = run_command("git branch -M main", cwd=BACKUP_DIR, check=False)
    result = run_command("git push -u origin main", cwd=BACKUP_DIR, check=False)
    
    if result.returncode != 0:
        print("  [提示] 推送失败，可能需要先在 GitHub 创建仓库")
        print(f"  请访问: https://github.com/new")
        print(f"  仓库名: diskcleaner-backup")
        return False
    
    print("  [OK] 推送成功!")
    return True


def restore_from_github():
    print_banner("从 GitHub 恢复")
    
    if not (BACKUP_DIR / ".git").exists():
        print("[步骤 1] 克隆仓库...")
        run_command(f"git clone {GITHUB_REPO} {BACKUP_DIR}")
    else:
        print("[步骤 1] 拉取最新...")
        run_command("git pull", cwd=BACKUP_DIR)
    
    print("\n[步骤 2] 恢复项目文件...")
    for item in PROJECT_FILES:
        src = BACKUP_DIR / item
        dst = PROJECT_ROOT / item
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"  [OK] {item}/")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  [OK] {item}")
    
    print("\n[步骤 3] 恢复 OpenClaw 数据...")
    openclaw_backup = BACKUP_DIR / "openclaw_data"
    if openclaw_backup.exists():
        for item in OPENCLAW_DATA:
            src = openclaw_backup / item
            dst = OPENCLAW_ROOT / item
            if src.exists():
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    print(f"  [OK] {item}/")
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    print(f"  [OK] {item}")
    
    print("\n" + "=" * 60)
    print("  [完成] 恢复完成！请重启 OpenClaw")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python github_sync.py --backup   # 上传")
        print("  python github_sync.py --restore  # 恢复")
        print("  python github_sync.py --status   # 状态")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "--backup":
        print_banner("上传 DiskCleaner 项目到 GitHub")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        create_gitignore()
        create_readme()
        backup_project_files()
        backup_openclaw_data()
        copy_sync_script()
        init_git_repo()
        commit_changes()
        push_to_github()
        
        print("\n" + "=" * 60)
        print("  [完成] 备份完成!")
        print("=" * 60)
        print(f"\nGitHub: {GITHUB_REPO}")
        
    elif action == "--restore":
        restore_from_github()
    else:
        print(f"未知操作: {action}")
        sys.exit(1)


if __name__ == "__main__":
    git_path = r"C:\Program Files\Git\bin\git.exe"
    if not Path(git_path).exists():
        print("[错误] 未找到 Git")
        sys.exit(1)
    main()
