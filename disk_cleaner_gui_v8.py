# -*- coding: utf-8 -*-
"""
C盘垃圾清理工具 v8.2 - 全新UI设计
现代化深色主题 + 标签页设计 + 渐变色彩
"""

import os
import sys
import ctypes
import shutil
import subprocess
import json
import base64
import sqlite3
import tempfile
import time
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import win32crypt
    HAS_WIN32CRYPT = True
except ImportError:
    HAS_WIN32CRYPT = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_AESGCM = True
except ImportError:
    HAS_AESGCM = False
import threading

# ========== 软件启动配置 ==========
SOFTWARE_CONFIG_FILE = os.path.join(os.path.expanduser('~'), 'DiskCleaner_software.json')

# ========== 账户权限控制 ==========
ALLOWED_USER = 'Administrator'

def get_current_username():
    """获取当前 Windows 用户名"""
    try:
        import getpass
        return getpass.getuser()
    except:
        try:
            return os.environ.get('USERNAME', os.environ.get('USER', ''))
        except:
            return ''


def get_resource_path(filename):
    """Resolve assets from either source checkout or the PyInstaller bundle."""
    base_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base_dir / filename

def is_admin_allowed():
    """检查当前账户是否有权限使用软件启动器"""
    return get_current_username() == ALLOWED_USER




# 默认软件列表
DEFAULT_SOFTWARE_LIST = [
    {
        'name': 'Visual Studio Code',
        'exe': 'Code.exe',
        'path': r'E:\Program Files\Microsoft VS Code\Code.exe',
        'icon': '💻',
        'color': '#007ACC'
    },
    {
        'name': 'UU远程',
        'exe': 'GameViewer.exe',
        'path': r'C:\Program Files\Netease\GameViewer\GameViewer.exe',
        'icon': '🎮',
        'color': '#E74C3C'
    },
    {
        'name': 'QClaw',
        'exe': 'QClaw.exe',
        'path': r'E:\Program Files\QClaw\v0.2.32.610\QClaw.exe',
        'icon': '🦷',
        'color': '#8B5CF6'
    },
    {
        'name': 'CC Switch',
        'exe': 'cc-switch.exe',
        'path': r'C:\Users\Administrator\AppData\Local\Programs\CC Switch\cc-switch.exe',
        'icon': '🔄',
        'color': '#10B981'
    },
    {
        'name': 'Internet Download Manager',
        'exe': 'IDMan.exe',
        'path': r'C:\Program Files (x86)\Internet Download Manager\IDMan.exe',
        'icon': '⬇️',
        'color': '#F59E0B'
    },
    {
        'name': 'MuMu模拟器',
        'exe': 'MuMuManager.exe',
        'path': r'D:\Program Files\Netease\MuMu\nx_main\MuMuManager.exe',
        'icon': '📱',
        'color': '#3B82F6'
    },
    {
        'name': 'Codex',
        'exe': 'Codex.exe',
        'path': r'D:\Codex\app\Codex.exe',
        'icon': '🤖',
        'color': '#6366F1'
    },
]

SOFTWARE_ICON_ASSETS = {
    'Visual Studio Code': 'vscode.png',
    'UU远程': 'uu_remote.png',
    'CC Switch': 'cc_switch.png',
    '夸克网盘': 'quark_cloud_drive.png',
    'MuMu模拟器': 'mumu.png',
    'Internet Download Manager': 'idm.png',
    'QClaw': 'qclaw.png',
    'ChatGPT': 'chatgpt.png',
    'Codex': 'chatgpt.png',
}
SOFTWARE_ICON_IMAGES = {}


def apply_software_icon_assets(software_list):
    """Associate known launcher entries with their supplied bitmap icons."""
    for software in software_list:
        icon_asset = SOFTWARE_ICON_ASSETS.get(software.get('name'))
        if icon_asset:
            software['icon_asset'] = icon_asset
    return software_list

def load_software_list():
    """加载软件列表"""
    if os.path.exists(SOFTWARE_CONFIG_FILE):
        try:
            with open(SOFTWARE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return apply_software_icon_assets(json.load(f))
        except:
            pass
    return apply_software_icon_assets(DEFAULT_SOFTWARE_LIST.copy())

def save_software_list(software_list):
    """保存软件列表"""
    with open(SOFTWARE_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(software_list, f, ensure_ascii=False, indent=2)

def launch_software(software):
    """启动软件（仅限 Administrator 账户）"""
    if not is_admin_allowed():
        return False, f"⚠️ 权限不足：该功能仅限 [{ALLOWED_USER}] 账户使用"
    exe_path = software.get('path', '')
    if not exe_path or not os.path.exists(exe_path):
        # 尝试在 PATH 中查找
        exe_name = software.get('exe', '')
        if exe_name:
            try:
                result = subprocess.run(
                    ['where', exe_name],
                    capture_output=True, text=True, creationflags=0x08000000
                )
                if result.returncode == 0:
                    exe_path = result.stdout.strip().split('\n')[0]
            except:
                pass
    
    if exe_path and os.path.exists(exe_path):
        try:
            subprocess.Popen(
                ['start', '', exe_path],
                shell=True,
                creationflags=0x08000000
            )
            return True, f"已启动 {software['name']}"
        except Exception as e:
            return False, str(e)
    else:
        return False, f"未找到: {exe_path or software.get('exe', '')}"

def check_software_running(software):
    """检查软件是否在运行"""
    exe_name = software.get('exe', '')
    if not exe_name:
        return False
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {exe_name}'],
            capture_output=True, text=True, creationflags=0x08000000
        )
        return exe_name in result.stdout
    except:
        return False


def hex_to_rgb(hex_color):
    """16进制颜色转RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    """RGB转16进制颜色"""
    return '#{:02X}{:02X}{:02X}'.format(int(r), int(g), int(b))

def draw_software_logo(parent, software, size=52):
    """绘制软件Logo - 渐变圆形背景 + 文字"""
    icon_asset = software.get('icon_asset')
    if icon_asset:
        asset_path = get_resource_path(Path('assets') / 'software-icons' / icon_asset)
        if asset_path.exists():
            try:
                image_key = str(asset_path)
                if image_key not in SOFTWARE_ICON_IMAGES:
                    SOFTWARE_ICON_IMAGES[image_key] = tk.PhotoImage(file=str(asset_path))
                canvas = tk.Canvas(
                    parent, width=size, height=size,
                    bg=COLORS['bg_card'], highlightthickness=0
                )
                canvas.create_image(size / 2, size / 2, image=SOFTWARE_ICON_IMAGES[image_key])
                return canvas
            except tk.TclError:
                pass

    color = software.get('color', '#6366F1')
    name = software.get('name', '?')
    icon = software.get('icon', '📦')

    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=COLORS['bg_card'], highlightthickness=0
    )

    # 渐变背景
    r1, g1, b1 = hex_to_rgb(color)
    # 渐变起点亮，终点暗
    r2, g2, b2 = max(0, r1 - 60), max(0, g1 - 60), max(0, b1 - 60)

    # 绘制渐变圆
    steps = 30
    for i in range(steps):
        t = i / steps
        r = r1 * (1 - t) + r2 * t
        g = g1 * (1 - t) + g2 * t
        b = b1 * (1 - t) + b2 * t
        offset = i * 0.5
        canvas.create_oval(
            2 + offset, 2 + offset,
            size - 2 - offset, size - 2 - offset,
            fill=rgb_to_hex(r, g, b), outline=''
        )

    # 高光 - 左上角柔光
    canvas.create_oval(
        8, 6, size * 0.55, size * 0.5,
        fill='', outline='white', width=0
    )
    # 半透明高光效果
    for i in range(8):
        t = i / 8
        a = int(60 * (1 - t))
        offset = i
        canvas.create_oval(
            10 + offset, 8 + offset,
            size * 0.5 + offset, size * 0.4 + offset,
            fill='', outline=rgb_to_hex(255, 255, 255), width=0
        )

    # 中心文字（取名称的首字母或emoji）
    center_text = ''
    if icon and ord(icon[0]) > 127:  # 是 emoji
        center_text = icon
    else:
        # 取首字
        if name:
            center_text = name[0].upper()
        else:
            center_text = '?'

    text_color = 'white'
    text_font = ('Segoe UI Emoji', 22) if ord(center_text[0]) > 127 else ('Microsoft YaHei UI', 22, 'bold')
    canvas.create_text(
        size/2, size/2,
        text=center_text, fill=text_color,
        font=text_font
    )

    return canvas


# ========== 保存的网络凭据配置 ==========
SAVED_CREDENTIALS = {
    'host': '192.168.0.44',
    'share': 'E$',
    'username': 'Admin',
    'password': '123',
    'description': '网络共享位置凭据'
}

# ========== 跟随 Windows 系统主题的色彩方案 ==========
THEME_PALETTES = {
    'light': {
        'bg_primary': '#FFFFFF',
        'bg_secondary': '#F7F7F8',
        'bg_card': '#FFFFFF',
        'bg_hover': '#EEF5FF',
        'gradient_start': '#007AFF',
        'gradient_end': '#006BE6',
        'gradient_accent': '#5AC8FA',
        'success': '#34C759',
        'warning': '#FF9500',
        'danger': '#FF3B30',
        'info': '#007AFF',
        'text_primary': '#1D1D1F',
        'text_secondary': '#515154',
        'text_muted': '#6E6E73',
        'border': '#E5E5E7',
        'border_light': '#D2D2D7',
    },
    'dark': {
        'bg_primary': '#1C1C1E',
        'bg_secondary': '#2C2C2E',
        'bg_card': '#2C2C2E',
        'bg_hover': '#243B53',
        'gradient_start': '#0A84FF',
        'gradient_end': '#0066CC',
        'gradient_accent': '#64D2FF',
        'success': '#30D158',
        'warning': '#FF9F0A',
        'danger': '#FF453A',
        'info': '#0A84FF',
        'text_primary': '#F5F5F7',
        'text_secondary': '#D1D1D6',
        'text_muted': '#98989D',
        'border': '#48484A',
        'border_light': '#636366',
    },
}

COLORS = THEME_PALETTES['light'].copy()

# The accepted UI reference is the light workbench. Keep it color-locked so
# Windows dark mode cannot turn the reference layout into a different design.
FOLLOW_SYSTEM_THEME = False
REFERENCE_THEME = 'light'

QUARK_WEBDAV_DRIVE = 'Q:'
QUARK_RCLONE_REMOTE = 'quark-device:'
QUARK_DRIVE_CONFIG_FILE = Path(os.path.expanduser('~')) / 'DiskCleaner_quark_drive.json'


def get_configured_quark_drive():
    """Read the persisted Explorer drive letter, falling back to X:."""
    try:
        payload = json.loads(QUARK_DRIVE_CONFIG_FILE.read_text(encoding='utf-8'))
        drive = str(payload.get('drive', '')).upper()
        if len(drive) == 2 and drive[0] in 'DEFGHIJKLMNOPQRSTUVWXYZ' and drive[1] == ':':
            return drive
    except (OSError, ValueError, TypeError):
        pass
    return 'X:'


def save_configured_quark_drive(drive):
    drive = drive.upper()
    if len(drive) != 2 or drive[0] not in 'DEFGHIJKLMNOPQRSTUVWXYZ' or drive[1] != ':':
        raise ValueError('请选择 D: 到 Z: 的盘符')
    QUARK_DRIVE_CONFIG_FILE.write_text(
        json.dumps({'drive': drive}, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    try:
        import winreg
        icon_key = (
            'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\DriveIcons\\'
            f'{drive[0]}\\DefaultIcon'
        )
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, icon_key) as registry_key:
            winreg.SetValueEx(
                registry_key, '', 0, winreg.REG_SZ,
                os.path.join(os.environ['SystemRoot'], 'System32', 'imageres.dll,-36')
            )
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except (OSError, AttributeError, KeyError):
        pass
    return drive


def get_available_quark_drives(selected_drive=None):
    """Offer only unused letters, while keeping the currently configured drive selectable."""
    selected_drive = (selected_drive or get_configured_quark_drive()).upper()
    available = []
    for letter in 'DEFGHIJKLMNOPQRSTUVWXYZ':
        drive = f'{letter}:'
        if drive == selected_drive or not os.path.exists(f'{drive}\\'):
            available.append(drive)
    return available


QUARK_DEVICE_DRIVE = get_configured_quark_drive()


def get_quark_backend_status():
    """Verify that the local Quark backend can actually read the cloud root."""
    try:
        check = subprocess.run(
            ['rclone', 'lsd', QUARK_RCLONE_REMOTE], capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=15,
            creationflags=0x08000000
        )
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)

    if check.returncode == 0:
        return True, '夸克网盘后端已连接'

    detail = (check.stderr or check.stdout).lower()
    if '401' in detail or 'unauthorized' in detail:
        return False, '夸克账号尚未授权，请扫描授权二维码后重试'
    if 'connection refused' in detail or 'connectex' in detail:
        return False, '夸克本机服务未启动'
    return False, '夸克网盘后端暂不可用'


def ensure_quark_device_drive():
    """Expose the mounted Quark root as a local drive in Explorer's device list."""
    if os.path.isdir(f'{QUARK_DEVICE_DRIVE}\\'):
        return True, f'夸克网盘已显示为 {QUARK_DEVICE_DRIVE}'

    try:
        configured = subprocess.run(
            ['rclone', 'listremotes'], capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=8
        )
        if QUARK_RCLONE_REMOTE not in configured.stdout.splitlines():
            return False, '未找到夸克 rclone 挂载配置'

        backend_ready, backend_message = get_quark_backend_status()
        if not backend_ready:
            return False, backend_message

        subprocess.Popen(
            ['rclone', 'mount', QUARK_RCLONE_REMOTE, QUARK_DEVICE_DRIVE,
             '--vfs-cache-mode', 'writes', '--dir-cache-time', '1m',
             '--volname', '夸克网盘', '--no-console'],
            creationflags=0x08000000
        )
        for _ in range(18):
            time.sleep(0.5)
            if os.path.isdir(f'{QUARK_DEVICE_DRIVE}\\'):
                return True, f'夸克网盘已挂载到 {QUARK_DEVICE_DRIVE}'
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)
    return False, f'{QUARK_DEVICE_DRIVE} 挂载超时'


def remove_quark_device_drive():
    """The virtual drive is owned by the rclone background mount."""
    return False, '请在退出 DiskCleaner 前保持夸克网盘连接'


def stop_quark_device_mounts():
    """Stop only rclone processes mounting the Quark remote, never other rclone jobs."""
    command = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -eq 'rclone.exe' -and $_.CommandLine -match 'mount\\s+quark-device:' "
        "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    try:
        subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', command],
            capture_output=True, text=True, timeout=12, creationflags=0x08000000
        )
    except (OSError, subprocess.SubprocessError):
        pass


def get_system_theme():
    """Use the approved reference palette, optionally following Windows later."""
    if not FOLLOW_SYSTEM_THEME:
        return REFERENCE_THEME
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        ) as key:
            apps_use_light_theme, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        return 'light' if apps_use_light_theme else 'dark'
    except (OSError, ImportError):
        return 'light'

# ========== 系统优化功能 ==========

def save_network_credentials():
    """保存网络凭据到 Windows 凭据管理器并映射 Z: 盘"""
    results = []
    try:
        # 1. 保存凭据
        cmd = [
            'cmdkey',
            f'/add:{SAVED_CREDENTIALS["host"]}',
            f'/user:{SAVED_CREDENTIALS["username"]}',
            f'/pass:{SAVED_CREDENTIALS["password"]}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        results.append(f"[OK] 凭据已保存: {SAVED_CREDENTIALS['host']}")

        # 2. 映射网络驱动器
        unc = f'\\\\{SAVED_CREDENTIALS["host"]}\\{SAVED_CREDENTIALS["share"]}'
        result = subprocess.run(
            ['net', 'use', 'Z:', unc, '/USER:' + SAVED_CREDENTIALS['username'],
             SAVED_CREDENTIALS['password'], '/PERSISTENT:YES'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0 or 'Z:' in result.stdout or '已连接' in result.stdout:
            results.append(f"[OK] Z: 盘已映射: {unc}")
        else:
            results.append(f"[WARN] 映射可能失败: {result.stdout}")

    except Exception as e:
        results.append(f"[ERROR] {str(e)}")

    return len([r for r in results if '[OK]' in r]) > 0, '\n'.join(results)

def check_network_credentials():
    """检查网络凭据是否已保存"""
    try:
        result = subprocess.run(
            ['cmdkey', '/list'],
            capture_output=True, text=True, shell=True
        )
        return SAVED_CREDENTIALS['host'] in result.stdout
    except:
        return False

def check_network_drive():
    """检查 Z: 盘是否已映射"""
    try:
        result = subprocess.run(
            ['net', 'use', 'Z:'],
            capture_output=True, text=True, shell=True
        )
        return result.returncode == 0
    except:
        return False

def disable_auto_backup():
    """禁用 Windows 自动备份任务"""
    results = []
    tasks = [
        r'\Microsoft\Windows\AppListBackup\Backup',
        r'\Microsoft\Windows\AppListBackup\BackupNonMaintenance'
    ]
    for task in tasks:
        try:
            result = subprocess.run(
                ['schtasks', '/Change', '/TN', task, '/Disable'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                results.append(f"[OK] 已禁用: {task}")
            else:
                results.append(f"[WARN] 可能不存在: {task}")
        except Exception as e:
            results.append(f"[ERROR] {task}: {str(e)}")
    return results

def check_backup_status():
    """检查备份任务是否已禁用"""
    try:
        result = subprocess.run(
            ['schtasks', '/Query', '/TN', r'\Microsoft\Windows\AppListBackup\Backup'],
            capture_output=True, text=True, shell=True
        )
        return '禁用' in result.stdout or result.returncode != 0
    except:
        return True

def disable_openclaw_backup():
    """禁用 OpenClaw 自动备份"""
    results = []

    # 1. 删除计划任务
    tasks = ['\\QClaw-Config-Backup', '\\QClaw-Config-Backup-New']
    for task in tasks:
        try:
            result = subprocess.run(
                ['schtasks', '/Delete', '/TN', task, '/F'],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if result.returncode == 0:
                results.append(f"[OK] 已删除计划任务: {task}")
            else:
                if '不存在' not in result.stderr and 'could not be found' not in result.stderr:
                    results.append(f"[INFO] 计划任务不存在: {task}")
        except Exception as e:
            results.append(f"[ERROR] 删除任务失败 {task}: {str(e)}")

    # 2. 删除备份脚本文件
    backup_dir = r'C:\Users\Administrator\.qclaw\workspace-agent-ed479baa'
    scripts = [
        'config-backup-runner-new.cmd',
        'config-backup-runner.cmd',
        'check_config_backup.ps1',
        'create-scheduled-tasks.ps1'
    ]

    for script in scripts:
        path = os.path.join(backup_dir, script)
        if os.path.exists(path):
            try:
                os.remove(path)
                results.append(f"[OK] 已删除: {script}")
            except Exception as e:
                results.append(f"[ERROR] 删除失败 {script}: {str(e)}")

    # 3. 清空 backups 目录
    backups_dirs = [
        os.path.join(backup_dir, 'backups'),
        r'C:\Users\Administrator\.qclaw\backups'
    ]
    for backups_dir in backups_dirs:
        if os.path.exists(backups_dir):
            try:
                for item in os.listdir(backups_dir):
                    item_path = os.path.join(backups_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                results.append(f"[OK] 已清空: {backups_dir}")
            except Exception as e:
                results.append(f"[ERROR] 清空失败 {backups_dir}: {str(e)}")

    return results, True

def check_openclaw_backup_status():
    """检查 OpenClaw 备份是否已禁用"""
    # 检查计划任务是否存在
    tasks = ['\\QClaw-Config-Backup', '\\QClaw-Config-Backup-New']
    for task in tasks:
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', task],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if result.returncode == 0:
                return False  # 任务存在，表示未禁用
        except:
            pass
    return True  # 任务不存在，表示已禁用

# ========== 进程管理功能 ==========

def get_processes_by_names(names):
    """通用进程检测函数"""
    processes = []
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('"')
                    if len(parts) >= 6:
                        name = parts[1]
                        pid = parts[3]
                        if any(n.lower() in name.lower() for n in names):
                            processes.append({'name': name, 'pid': int(pid)})
    except Exception as e:
        print(f"Error: {e}")
    return processes

def kill_processes_by_names(names):
    """通用进程关闭函数"""
    results = []
    killed_count = 0
    try:
        for name in names:
            result = subprocess.run(
                ['taskkill', '/F', '/IM', name],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and '成功' in result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '成功' in line:
                        killed_count += 1
                results.append(f"[OK] taskkill /IM {name}")

        processes = get_processes_by_names(names)
        for proc in processes:
            try:
                result = subprocess.run(
                    ['taskkill', '/F', '/PID', str(proc['pid'])],
                    capture_output=True, text=True, shell=True
                )
                if result.returncode == 0:
                    killed_count += 1
                    results.append(f"[OK] 关闭 {proc['name']} (PID: {proc['pid']})")
            except:
                pass

        if killed_count > 0:
            results.insert(0, f"共关闭 {killed_count} 个进程")
        else:
            results.insert(0, "未找到运行中的进程")

    except Exception as e:
        results.append(f"[ERROR] {str(e)}")

    return results, killed_count > 0

# 各进程名称列表
CODEX_NAMES = ['codex.exe', 'codex']
GOOGLE_NAMES = ['chrome.exe', 'googlechrome.exe', 'googledrive.exe', 'googleupdate.exe']
QCLAW_NAMES = ['QClaw.exe', 'openclaw.exe']
CC_SWITCH_NAMES = ['ccswitch.exe', 'cc-switch.exe', 'CCSwitch.exe']
CLASH_VERGE_NAMES = ['Clash Verge.exe', 'clash-verge.exe', 'clash-verge-rev.exe']

# ========== 磁盘信息获取 ==========

def get_disk_info():
    """获取 C 盘信息"""
    try:
        free_bytes = ctypes.c_uint64()
        total_bytes = ctypes.c_uint64()
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p('C:'),
            None,
            ctypes.byref(total_bytes),
            ctypes.byref(free_bytes)
        )
        total = total_bytes.value
        free = free_bytes.value
        used = total - free
        percent = int(used * 100 / total) if total > 0 else 0
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent': percent
        }
    except:
        return None

def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

# ========== 扫描和清理功能 ==========

def get_all_user_profiles():
    """获取所有用户配置文件目录"""
    users_dir = 'C:\\Users'
    profiles = []
    excluded = ['All Users', 'Default', 'Default User', 'Public']
    try:
        if os.path.exists(users_dir):
            for item in os.listdir(users_dir):
                profile_path = os.path.join(users_dir, item)
                # 排除系统目录和非用户目录
                if item not in excluded and os.path.isdir(profile_path):
                    profiles.append((item, profile_path))
                    print(f"[DEBUG] 发现用户: {item}")
                else:
                    print(f"[DEBUG] 跳过: {item}")
        else:
            print(f"[DEBUG] Users目录不存在: {users_dir}")
    except Exception as e:
        print(f"[DEBUG] 获取用户列表失败: {e}")
    print(f"[DEBUG] 共发现 {len(profiles)} 个用户")
    return profiles

def get_paths_to_clean():
    """获取需要清理的路径 - 包含所有用户账户(Administrator浏览器缓存标记为手动删除)"""
    paths = []

    # 1. 系统级路径
    paths.extend([
        {'name': '系统临时文件', 'path': 'C:\\Windows\\Temp', 'manual': False},
        {'name': '崩溃转储', 'path': 'C:\\Windows\\Minidump', 'manual': False},
        {'name': '回收站', 'path': 'C:\\$Recycle.Bin', 'manual': False},
    ])

    # 2. 所有用户的缓存路径
    user_profiles = get_all_user_profiles()
    print(f"[DEBUG] 开始处理 {len(user_profiles)} 个用户的缓存路径")

    for username, profile_path in user_profiles:
        print(f"[DEBUG] 处理用户: {username}, 路径: {profile_path}")

        # 判断是否为 Administrator 账户
        is_admin_user = username.lower() == 'administrator'

        # 用户临时文件 - 所有用户都清理
        temp_path = os.path.join(profile_path, 'AppData', 'Local', 'Temp')
        print(f"[DEBUG]   检查: {temp_path} -> 存在: {os.path.exists(temp_path)}")
        if os.path.exists(temp_path):
            paths.append({'name': f'{username} - 临时文件', 'path': temp_path, 'manual': False})

        # IE/Edge 浏览器缓存
        inet_cache = os.path.join(profile_path, 'AppData', 'Local', 'Microsoft', 'Windows', 'INetCache')
        print(f"[DEBUG]   检查: {inet_cache} -> 存在: {os.path.exists(inet_cache)}")
        if os.path.exists(inet_cache):
            # Administrator 标记为手动删除,其他用户自动清理
            paths.append({'name': f'{username} - IE缓存', 'path': inet_cache, 'manual': is_admin_user})

        # Edge 浏览器缓存
        edge_cache = os.path.join(profile_path, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache')
        print(f"[DEBUG]   检查: {edge_cache} -> 存在: {os.path.exists(edge_cache)}")
        if os.path.exists(edge_cache):
            # Administrator 标记为手动删除,其他用户自动清理
            paths.append({'name': f'{username} - Edge缓存', 'path': edge_cache, 'manual': is_admin_user})

        # Firefox 缓存
        firefox_profile = os.path.join(profile_path, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles')
        print(f"[DEBUG]   检查: {firefox_profile} -> 存在: {os.path.exists(firefox_profile)}")
        if os.path.exists(firefox_profile):
            try:
                for ff_profile in os.listdir(firefox_profile):
                    ff_cache = os.path.join(firefox_profile, ff_profile, 'cache2')
                    if os.path.exists(ff_cache):
                        # Administrator 标记为手动删除,其他用户自动清理
                        paths.append({'name': f'{username} - Firefox缓存', 'path': ff_cache, 'manual': is_admin_user})
                        break  # 只取第一个配置文件的缓存
            except Exception as e:
                print(f"[DEBUG]   Firefox缓存检查失败: {e}")

        # Windows 更新缓存 - 所有用户都清理
        software_distribution = os.path.join(profile_path, 'AppData', 'Local', 'Microsoft', 'Windows', 'SoftwareDistribution', 'Download')
        print(f"[DEBUG]   检查: {software_distribution} -> 存在: {os.path.exists(software_distribution)}")
        if os.path.exists(software_distribution):
            paths.append({'name': f'{username} - 更新缓存', 'path': software_distribution, 'manual': False})

        # 缩略图缓存 - 所有用户都清理
        thumb_cache = os.path.join(profile_path, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer')
        print(f"[DEBUG]   检查: {thumb_cache} -> 存在: {os.path.exists(thumb_cache)}")
        if os.path.exists(thumb_cache):
            # 查找 thumbcache_*.db 文件
            try:
                has_thumb = False
                for f in os.listdir(thumb_cache):
                    if f.startswith('thumbcache_'):
                        has_thumb = True
                        break
                if has_thumb:
                    paths.append({'name': f'{username} - 缩略图缓存', 'path': thumb_cache, 'manual': False})
                    print(f"[DEBUG]   发现缩略图缓存文件")
            except Exception as e:
                print(f"[DEBUG]   缩略图缓存检查失败: {e}")

    print(f"[DEBUG] 共生成 {len(paths)} 个清理路径")
    return paths

def fast_scan_size(path):
    """快速扫描目录大小"""
    total = 0
    file_count = 0
    error_count = 0
    try:
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    total += os.path.getsize(fp)
                    file_count += 1
                except Exception as e:
                    error_count += 1
    except Exception as e:
        print(f"[DEBUG] 扫描目录失败 {path}: {e}")
    print(f"[DEBUG]   扫描结果: {file_count} 个文件, {total} 字节, {error_count} 个错误")
    return total

def clear_directory(path, timeout=30):
    """清理目录 - 带超时保护"""
    count = 0
    size = 0
    errors = []
    if not os.path.exists(path):
        return 0, 0, []

    start_time = datetime.now()

    try:
        for root, dirs, files in os.walk(path, topdown=True):
            # 检查是否超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                errors.append(f"清理超时 ({timeout}秒)")
                break

            # 清理文件
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    file_size = os.path.getsize(fp)
                    os.remove(fp)
                    size += file_size
                    count += 1
                except Exception as e:
                    pass

            # 清理空目录
            for d in dirs:
                try:
                    dp = os.path.join(root, d)
                    if os.path.isdir(dp):
                        os.rmdir(dp)
                except:
                    pass
    except Exception as e:
        errors.append(str(e))

    return count, size, errors

# ========== 管理员权限检查 ==========

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if sys.platform == 'win32':
        try:
            if getattr(sys, 'frozen', False):
                script = sys.executable
            else:
                script = os.path.abspath(__file__)
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas",
                sys.executable if not getattr(sys, 'frozen', False) else script,
                f'"{script}"' if not getattr(sys, 'frozen', False) else '',
                None, 1
            )
            sys.exit(0)
        except:
            return False
    return False

# ========== 浏览器 Cookie 抓取 ==========

BROWSER_COOKIE_PATHS = {
    'edge':   os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data'),
    'chrome': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data'),
    'brave':  os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data'),
    '360chrome': os.path.expandvars(r'%LOCALAPPDATA%\360Chrome\Chrome\User Data'),
    'qqbrowser': os.path.expandvars(r'%LOCALAPPDATA%\Tencent\QQBrowser\User Data'),
}

BROWSER_DISPLAY_NAMES = {
    'edge': 'Edge',
    'chrome': 'Chrome',
    'brave': 'Brave',
    '360chrome': '360 极速浏览器',
    'qqbrowser': 'QQ 浏览器',
}

def find_browser_cookie_db(base_dir):
    """查找浏览器 Cookies 数据库路径"""
    if not os.path.exists(base_dir):
        return None, None
    # Default profile first
    default_path = os.path.join(base_dir, 'Default', 'Network', 'Cookies')
    if os.path.exists(default_path):
        return default_path, 'Default'
    # 找其他 profile
    for entry in os.listdir(base_dir):
        if entry.startswith('Profile '):
            full = os.path.join(base_dir, entry, 'Network', 'Cookies')
            if os.path.exists(full):
                return full, entry
    # 旧版 Chrome 可能没 Network 子目录
    legacy = os.path.join(base_dir, 'Default', 'Cookies')
    if os.path.exists(legacy):
        return legacy, 'Default'
    for entry in os.listdir(base_dir):
        if entry.startswith('Profile '):
            full = os.path.join(base_dir, entry, 'Cookies')
            if os.path.exists(full):
                return full, entry
    return None, None

def get_browser_encryption_key(base_dir):
    """从 Local State 读取浏览器加密密钥"""
    local_state = os.path.join(base_dir, 'Local State')
    if not os.path.exists(local_state):
        return None
    try:
        with open(local_state, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'os_crypt' not in data or 'encrypted_key' not in data['os_crypt']:
            return None
        encrypted_key = base64.b64decode(data['os_crypt']['encrypted_key'])
        # 移除 "DPAPI" 前缀 (5 字节)
        if encrypted_key[:5] != b'DPAPI':
            return None
        encrypted_key = encrypted_key[5:]
        if not HAS_WIN32CRYPT:
            return None
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception:
        return None

def decrypt_cookie_value(encrypted_value, key):
    """解密 Chrome/Edge cookie 值 (v10/v11 AES-GCM 或 DPAPI)"""
    if not encrypted_value:
        return ''
    try:
        # v10 / v11 = AES-256-GCM
        if encrypted_value[:3] in (b'v10', b'v11') and key and HAS_AESGCM:
            nonce = encrypted_value[3:15]
            # GCM: ciphertext + 16-byte tag 合并传入
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, encrypted_value[3:], None).decode('utf-8', errors='replace')
        # 旧版 DPAPI 加密
        if HAS_WIN32CRYPT:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8', errors='replace')
        return ''
    except Exception as e:
        return f'[解密错误: {e}]'

def extract_quark_cookies_from_browser(browser_key):
    """从指定浏览器抓取夸克网盘 Cookie"""
    base_dir = BROWSER_COOKIE_PATHS.get(browser_key)
    if not base_dir or not os.path.exists(base_dir):
        return None, f"{BROWSER_DISPLAY_NAMES.get(browser_key, browser_key)} 未安装"

    cookies_db, profile = find_browser_cookie_db(base_dir)
    if not cookies_db:
        return None, f"未找到 Cookies 数据库 (请先登录夸克网盘)"

    key = get_browser_encryption_key(base_dir)

    # 复制数据库避免锁冲突
    tmp_db = os.path.join(tempfile.gettempdir(), f'dc_cookies_{browser_key}.db')
    try:
        shutil.copy2(cookies_db, tmp_db)
    except PermissionError:
        return None, f"无法读取 Cookies (浏览器正在运行,请先完全关闭 {BROWSER_DISPLAY_NAMES.get(browser_key, browser_key)})"
    except Exception as e:
        return None, f"复制数据库失败: {e}"

    found = {}
    try:
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, encrypted_value, host_key FROM cookies WHERE host_key LIKE '%quark.cn' AND name IN ('__pus', '__puus')"
        )
        for name, enc, host in cursor.fetchall():
            if enc:
                val = decrypt_cookie_value(enc, key)
                found[name] = val
        conn.close()
    except Exception as e:
        return None, f"读取数据库失败: {e}"
    finally:
        try:
            os.unlink(tmp_db)
        except:
            pass

    if not found:
        return None, "未找到夸克网盘 Cookie (请先在该浏览器中登录 pan.quark.cn)"
    return found, None

def extract_quark_cookies_auto():
    """自动扫描所有浏览器抓取夸克 Cookie"""
    results = {}
    errors = {}
    for key in BROWSER_COOKIE_PATHS.keys():
        if not os.path.exists(BROWSER_COOKIE_PATHS[key]):
            continue
        cookies, err = extract_quark_cookies_from_browser(key)
        if cookies:
            results[key] = cookies
        elif err:
            errors[key] = err
    return results, errors

# ========== 主应用类 ==========

class App:
    def __init__(self, root):
        self.root = root
        self.current_theme = get_system_theme()
        COLORS.update(THEME_PALETTES[self.current_theme])
        self.root.title("DiskCleaner")
        icon_path = get_resource_path('app_icon.png')
        icon_ico_path = get_resource_path('app_icon.ico')
        if icon_ico_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_ico_path))
            except tk.TclError:
                pass
        if icon_path.exists():
            try:
                self.window_icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self.window_icon)
            except tk.TclError:
                pass
        # The overview is designed against the supplied 1584 x 991 reference.
        self.root.geometry("1280x800")
        self.root.minsize(1060, 680)
        self.root.configure(bg=COLORS['bg_primary'])

        # 数据
        self.scan_results = []
        self.total_size = 0
        self.is_scanning = False
        self.is_cleaning = False

        # 创建 UI
        self.create_widgets()

        # 初始化检查
        self.root.after(100, self.check_system_status)
        self.root.after(1000, self.watch_system_theme)

    def create_widgets(self):
        """创建主界面"""
        # The native title bar already carries the app name; keep the content area quiet.
        self.create_notebook()
        self.create_status_bar()

    def configure_ttk_styles(self):
        """Apply palette values to the ttk controls used by the app."""
        style = ttk.Style()
        style.theme_use('default')
        style.layout('Hidden.TNotebook.Tab', [])
        style.configure('Hidden.TNotebook', background=COLORS['bg_primary'], borderwidth=0)
        style.configure('TNotebook', background=COLORS['bg_primary'], borderwidth=0)
        style.configure(
            'TNotebook.Tab', background=COLORS['bg_secondary'],
            foreground=COLORS['text_secondary'], padding=[20, 10],
            font=('Microsoft YaHei', 10)
        )
        style.map(
            'TNotebook.Tab',
            background=[('selected', COLORS['bg_card'])],
            foreground=[('selected', COLORS['text_primary'])]
        )
        style.configure(
            'TProgressbar', background=COLORS['gradient_start'],
            troughcolor=COLORS['bg_secondary'], bordercolor=COLORS['border'],
            lightcolor=COLORS['gradient_start'], darkcolor=COLORS['gradient_end']
        )

    def watch_system_theme(self):
        """Refresh the app when Windows switches between light and dark mode."""
        system_theme = get_system_theme()
        if system_theme != self.current_theme:
            self.apply_theme(system_theme)
        self.root.after(1000, self.watch_system_theme)

    def apply_theme(self, theme_name):
        """Update existing Tk widgets from the previous semantic palette."""
        previous_colors = COLORS.copy()
        COLORS.update(THEME_PALETTES[theme_name])
        self.current_theme = theme_name
        color_map = {
            old.lower(): COLORS[key]
            for key, old in previous_colors.items()
            if key in COLORS
        }
        self.root.configure(bg=COLORS['bg_primary'])
        self.refresh_widget_theme(self.root, color_map)
        self.configure_ttk_styles()
        if hasattr(self, 'logo_canvas'):
            self.logo_canvas.itemconfigure('logo_background', fill=COLORS['gradient_start'])
        if hasattr(self, 'storage_canvas'):
            self.draw_storage_bar()
        if hasattr(self, 'notebook'):
            self.select_tab(self.notebook.index(self.notebook.select()))

    def refresh_widget_theme(self, widget, color_map):
        """Replace palette colors on existing Tk widgets without rebuilding state."""
        color_options = (
            'background', 'foreground', 'activebackground', 'activeforeground',
            'highlightbackground', 'highlightcolor', 'insertbackground', 'selectcolor',
            'troughcolor'
        )
        for option in color_options:
            try:
                current_color = widget.cget(option)
            except tk.TclError:
                continue
            replacement = color_map.get(str(current_color).lower())
            if replacement:
                try:
                    widget.configure(**{option: replacement})
                except tk.TclError:
                    pass
        for child in widget.winfo_children():
            self.refresh_widget_theme(child, color_map)

    def create_header(self):
        """创建顶部标题栏"""
        header = tk.Frame(self.root, bg=COLORS['bg_secondary'], height=70)
        header.pack(fill='x', padx=0, pady=0)
        header.pack_propagate(False)

        # 左侧 Logo 和标题
        left_frame = tk.Frame(header, bg=COLORS['bg_secondary'])
        left_frame.pack(side='left', padx=20, pady=15)

        # Logo 图标 (使用渐变效果的文字)
        from tkinter import font as tkfont
        logo_canvas = tk.Canvas(
            left_frame, width=44, height=44,
            bg=COLORS['bg_secondary'], highlightthickness=0
        )
        logo_canvas.pack(side='left', padx=(0, 10))
        # 画一个圆形背景
        logo_canvas.create_oval(
            2, 2, 42, 42, fill=COLORS['gradient_start'], outline='',
            tags='logo_background'
        )
        # 画一个闪电/火箭图标文字
        logo_canvas.create_text(22, 22, text='🚀', font=('Segoe UI Emoji', 18), fill='white')
        self.logo_canvas = logo_canvas

        # 标题和副标题
        title_frame = tk.Frame(left_frame, bg=COLORS['bg_secondary'])
        title_frame.pack(side='left')

        title_label = tk.Label(
            title_frame,
            text="DiskCleaner",
            font=('Microsoft YaHei', 20, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary']
        )
        title_label.pack(anchor='w')

        subtitle_label = tk.Label(
            title_frame,
            text="轻量、清晰、可控的系统维护工具",
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_muted']
        )
        subtitle_label.pack(anchor='w')

        # 右侧 C 盘信息
        self.create_disk_info(header)

    def create_disk_info(self, parent):
        """创建 C 盘信息显示"""
        info_frame = tk.Frame(parent, bg=COLORS['bg_secondary'])
        info_frame.pack(side='right', padx=20, pady=10)

        # C 盘标签
        tk.Label(
            info_frame,
            text="C 盘状态",
            font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary']
        ).pack(anchor='w')

        # 使用率
        self.disk_percent = tk.Label(
            info_frame,
            text="--%",
            font=('Microsoft YaHei', 24, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['warning']
        )
        self.disk_percent.pack(anchor='w')

        # 详细信息
        self.disk_detail = tk.Label(
            info_frame,
            text="加载中...",
            font=('Microsoft YaHei', 8),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_muted']
        )
        self.disk_detail.pack(anchor='w')

    def create_notebook(self):
        # Exact workbench proportions from the supplied reference image.
        self.configure_ttk_styles()
        shell = tk.Frame(self.root, bg=COLORS['bg_primary'])
        shell.pack(fill='both', expand=True)

        self.sidebar = tk.Frame(
            shell, bg='#FBFCFF', width=250,
            highlightbackground='#E2E5EA', highlightthickness=1
        )
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        tk.Frame(self.sidebar, bg='#FBFCFF', height=38).pack(fill='x')

        content = tk.Frame(shell, bg=COLORS['bg_primary'])
        content.pack(side='left', fill='both', expand=True, padx=(26, 26), pady=(12, 17))
        self.notebook = ttk.Notebook(content, style='Hidden.TNotebook')
        self.notebook.pack(fill='both', expand=True)

        self.create_scan_tab()
        self.create_optimize_tab()
        self.create_process_tab()
        self.create_cloud_tab()
        self.create_launcher_tab()

        nav_items = [
            ('◕', '清理概览'), ('◴', '系统优化'), ('⌁', '进程管理'),
            ('☁', '云端同步'), ('▦', '软件启动')
        ]
        self.nav_buttons = []
        for index, (icon, label) in enumerate(nav_items):
            row = tk.Frame(self.sidebar, bg='#FBFCFF', height=61, cursor='hand2')
            row.pack(fill='x', padx=11, pady=6)
            row.pack_propagate(False)
            accent = tk.Frame(row, bg='#FBFCFF', width=4)
            accent.pack(side='left', fill='y')
            icon_label = tk.Label(
                row, text=icon, width=2, anchor='center',
                font=('Segoe UI Symbol', 25), bg='#FBFCFF', fg='#4B4D52'
            )
            icon_label.pack(side='left', padx=(13, 8))
            text_label = tk.Label(
                row, text=label, anchor='w',
                font=('Microsoft YaHei UI', 12), bg='#FBFCFF', fg='#4B4D52'
            )
            text_label.pack(side='left', fill='both', expand=True)
            for widget in (row, accent, icon_label, text_label):
                widget.bind('<Button-1>', lambda _event, i=index: self.select_tab(i))
            self.nav_buttons.append((row, accent, icon_label, text_label))
        self.select_tab(0)

        self.root.after(500, self.refresh_optimize_status)
        self.root.after(700, self.check_all_processes)
        self.root.after(900, self.refresh_cloud_status)

    def select_tab(self, index):
        """Switch the content page and update the selected navigation row."""
        self.notebook.select(index)
        for i, navigation in enumerate(getattr(self, 'nav_buttons', [])):
            if not isinstance(navigation, tuple):
                continue
            row, accent, icon_label, text_label = navigation
            selected = i == index
            background = '#F3F8FF' if selected else '#FBFCFF'
            foreground = '#1677FF' if selected else '#4B4D52'
            row.configure(bg=background)
            accent.configure(bg='#1677FF' if selected else background)
            icon_label.configure(bg=background, fg=foreground)
            text_label.configure(
                bg=background, fg=foreground,
                font=('Microsoft YaHei UI', 12, 'bold' if selected else 'normal')
            )
        if self.nav_buttons and isinstance(self.nav_buttons[0], tuple):
            return
        self.notebook.select(index)
        for i, button in enumerate(getattr(self, 'nav_buttons', [])):
            selected = i == index
            button.configure(
                bg=COLORS['bg_hover'] if selected else COLORS['bg_secondary'],
                fg=COLORS['text_primary'] if selected else COLORS['text_secondary'],
                font=('Microsoft YaHei', 10, 'bold' if selected else 'normal')
            )

    def create_scan_tab(self):
        """创建扫描清理标签页"""
        self.create_dashboard_scan_tab()

    def create_reference_scan_layout(self):
        """Recreate the supplied cleanup-overview screen at its original density."""
        self.dashboard_scan = True
        tab_host = tk.Frame(self.notebook, bg='#FFFFFF')
        self.notebook.add(tab_host, text='清理概览')
        self.overview_canvas = tk.Canvas(tab_host, bg='#FFFFFF', highlightthickness=0, bd=0)
        self.overview_scrollbar = ttk.Scrollbar(
            tab_host, orient='vertical', command=self.overview_canvas.yview
        )
        self.overview_canvas.configure(yscrollcommand=self.overview_scrollbar.set)
        self.overview_canvas.pack(side='left', fill='both', expand=True)
        self.overview_scrollbar.pack(side='right', fill='y')

        tab = tk.Frame(self.overview_canvas, bg='#FFFFFF')
        overview_window = self.overview_canvas.create_window((0, 0), window=tab, anchor='nw')
        tab.bind(
            '<Configure>',
            lambda _event: self.overview_canvas.configure(
                scrollregion=self.overview_canvas.bbox('all')
            )
        )
        self.overview_canvas.bind(
            '<Configure>',
            lambda event: self.overview_canvas.itemconfigure(overview_window, width=event.width)
        )

        def scroll_overview(event):
            self.overview_canvas.yview_scroll(-int(event.delta / 120), 'units')
            return 'break'

        self.overview_canvas.bind('<MouseWheel>', scroll_overview)
        tab.bind('<MouseWheel>', scroll_overview)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=0, minsize=360)

        header = tk.Frame(tab, bg='#FFFFFF', height=49)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        tk.Label(
            header, text='清理概览', font=('Microsoft YaHei UI', 24, 'bold'),
            bg='#FFFFFF', fg='#1D1D1F'
        ).pack(side='left', anchor='w')
        overview_status = tk.Frame(header, bg='#FFFFFF')
        overview_status.pack(side='right', anchor='s', pady=(0, 7))
        tk.Label(overview_status, text='磁盘使用情况：', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#5F6368').pack(side='left')
        self.disk_percent = tk.Label(overview_status, text='--%', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#3C4043')
        self.disk_percent.pack(side='left', padx=(4, 35))
        tk.Label(overview_status, text='●', font=('Microsoft YaHei UI', 16), bg='#FFFFFF', fg='#19C15A').pack(side='left', padx=(0, 9))
        tk.Label(overview_status, text='系统状态：良好', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#5F6368').pack(side='left')

        storage = tk.Frame(tab, bg='#FFFFFF', height=191, highlightbackground='#DFE2E6', highlightthickness=1)
        storage.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        storage.grid_propagate(False)
        storage_inner = tk.Frame(storage, bg='#FFFFFF')
        storage_inner.pack(fill='both', expand=True, padx=19, pady=15)
        storage_title = tk.Frame(storage_inner, bg='#FFFFFF')
        storage_title.pack(fill='x')
        tk.Label(storage_title, text='C盘空间', font=('Microsoft YaHei UI', 20), bg='#FFFFFF', fg='#202124').pack(side='left')
        self.disk_free_label = tk.Label(storage_title, text='可用：--', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#5F6368')
        self.disk_free_label.pack(side='right', pady=(5, 0))
        self.disk_detail = tk.Label(storage_inner, text='已用：加载中...', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#5F6368')
        self.disk_detail.pack(anchor='w', pady=(12, 14))
        self.storage_canvas = tk.Canvas(storage_inner, height=31, bg='#FFFFFF', highlightthickness=0, bd=0)
        self.storage_canvas.pack(fill='x')
        self.storage_canvas.bind('<Configure>', lambda _event: self.draw_storage_bar())
        self.storage_info = None
        legend = tk.Frame(storage_inner, bg='#FFFFFF')
        legend.pack(fill='x', pady=(10, 0))
        for color, text in [
            ('#1677FF', '系统文件  81.6 GB (34%)'), ('#22C55E', '应用程序  45.3 GB (19%)'),
            ('#FF9F0A', '用户文件  28.7 GB (12%)'), ('#FF453A', '其他  15.6 GB (6%)'),
            ('#D4D7DC', '可用空间  66.1 GB (28%)')
        ]:
            item = tk.Frame(legend, bg='#FFFFFF')
            item.pack(side='left', padx=(0, 39))
            tk.Label(item, text='●', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg=color).pack(side='left')
            tk.Label(item, text=text, font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#5F6368').pack(side='left', padx=(6, 0))

        cleanup_heading = tk.Frame(tab, bg='#FFFFFF', height=80)
        cleanup_heading.grid(row=2, column=0, sticky='ew')
        cleanup_heading.grid_propagate(False)
        copy = tk.Frame(cleanup_heading, bg='#FFFFFF')
        copy.pack(side='left', anchor='n', pady=(5, 0))
        tk.Label(copy, text='安全可清理', font=('Microsoft YaHei UI', 21, 'bold'), bg='#FFFFFF', fg='#202124').pack(anchor='w')
        self.cleanup_subtitle = tk.Label(copy, text='扫描系统中不必要的文件，释放磁盘空间。', font=('Microsoft YaHei UI', 12), bg='#FFFFFF', fg='#6B7078')
        self.cleanup_subtitle.pack(anchor='w', pady=(7, 0))
        self.cleanup_action_frame = tk.Frame(cleanup_heading, bg='#FFFFFF', width=138, height=62)
        self.cleanup_action_frame.pack(side='right', anchor='n', pady=(4, 0))
        self.cleanup_action_frame.pack_propagate(False)
        self.scan_btn = tk.Button(
            self.cleanup_action_frame, text='开始扫描', font=('Microsoft YaHei UI', 13, 'bold'),
            bg='#1677FF', fg='#FFFFFF', activebackground='#0969E8', activeforeground='#FFFFFF',
            relief='flat', bd=0, width=12, height=2, cursor='hand2', command=self.start_scan
        )
        self.scan_btn.place(x=0, y=0, width=138, height=62)
        self.clean_btn = tk.Button(
            self.cleanup_action_frame, text='立即清理', font=('Microsoft YaHei UI', 13, 'bold'),
            bg='#FF453A', fg='#FFFFFF', activebackground='#E23B30', activeforeground='#FFFFFF',
            relief='flat', bd=0, width=12, height=2, cursor='hand2', command=self.start_clean, state='disabled'
        )

        table = tk.Frame(tab, bg='#FFFFFF', highlightbackground='#DFE2E6', highlightthickness=1)
        table.grid(row=3, column=0, sticky='nsew')
        table.grid_columnconfigure(0, weight=1)
        table.grid_columnconfigure(1, weight=0)
        table.grid_rowconfigure(1, weight=1)
        table_header = tk.Frame(table, bg='#FFFFFF', height=44)
        table_header.grid(row=0, column=0, sticky='ew')
        table_header.grid_propagate(False)
        for col, weight, minsize in ((0, 0, 72), (1, 0, 390), (2, 1, 0), (3, 0, 175)):
            table_header.grid_columnconfigure(col, weight=weight, minsize=minsize)
        for col, text, anchor in ((0, '□', 'center'), (1, '项目', 'w'), (2, '说明', 'w'), (3, '预计可释放', 'e')):
            tk.Label(table_header, text=text, font=('Microsoft YaHei UI', 11, 'bold'), bg='#FFFFFF', fg='#3C4043', anchor=anchor).grid(row=0, column=col, sticky='nsew', padx=18)
        tk.Frame(table, bg='#E7E9ED', height=1).grid(row=0, column=0, sticky='sew')
        self.result_canvas = tk.Canvas(table, bg='#FFFFFF', highlightthickness=0, bd=0)
        self.result_canvas.grid(row=1, column=0, sticky='nsew')
        self.result_scrollbar = ttk.Scrollbar(
            table, orient='vertical', command=self.result_canvas.yview
        )
        self.result_scrollbar.grid(row=1, column=1, sticky='ns')
        self.result_canvas.configure(yscrollcommand=self.result_scrollbar.set)
        self.result_container = tk.Frame(self.result_canvas, bg='#FFFFFF')
        self.result_window = self.result_canvas.create_window((0, 0), window=self.result_container, anchor='nw')
        self.result_container.bind('<Configure>', lambda _event: self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all')))
        self.result_canvas.bind('<Configure>', self.resize_result_window)

        def scroll_cleanup_results(event):
            self.result_canvas.yview_scroll(-int(event.delta / 120), 'units')
            return 'break'

        self.result_canvas.bind('<MouseWheel>', scroll_cleanup_results)
        self.result_container.bind('<MouseWheel>', scroll_cleanup_results)
        self.render_dashboard_preview()

        recent = tk.Frame(tab, bg='#FFFFFF', height=128)
        recent.grid(row=4, column=0, sticky='ew', pady=(16, 0))
        recent.grid_propagate(False)
        tk.Label(recent, text='最近扫描', font=('Microsoft YaHei UI', 15, 'bold'), bg='#FFFFFF', fg='#202124').pack(anchor='w', pady=(0, 8))
        recent_table = tk.Frame(recent, bg='#FFFFFF', height=93, highlightbackground='#DFE2E6', highlightthickness=1)
        recent_table.pack(fill='x')
        recent_table.pack_propagate(False)
        headers = [('时间', 2), ('类型', 2), ('扫描项', 5), ('发现大小', 2), ('操作', 1)]
        for col, (text, weight) in enumerate(headers):
            recent_table.grid_columnconfigure(col, weight=weight)
            tk.Label(recent_table, text=text, font=('Microsoft YaHei UI', 11, 'bold'), bg='#FFFFFF', fg='#3C4043', anchor='w').grid(row=0, column=col, sticky='ew', padx=18, pady=(10, 8))
        tk.Frame(recent_table, bg='#E7E9ED', height=1).grid(row=1, column=0, columnspan=5, sticky='ew')
        self.recent_result = tk.Label(recent_table, text='尚未扫描', font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#6B7078', anchor='w')
        self.recent_result.grid(row=2, column=0, columnspan=5, sticky='ew', padx=18, pady=10)

        self.progress_var = tk.DoubleVar()
        self.scan_stats = tk.Label(tab)
        self.clean_stats = tk.Label(tab)
        self.log_text = tk.Text(tab, height=1, width=1)
        self.root.after(50, self.update_disk_info)

    def create_dashboard_scan_tab(self):
        """Build the reference-style cleanup overview without changing scan behavior."""
        self.create_reference_scan_layout()

    def resize_result_window(self, event):
        self.result_canvas.itemconfigure(self.result_window, width=event.width)

    def draw_storage_bar(self):
        if not getattr(self, 'storage_info', None):
            return
        canvas = self.storage_canvas
        canvas.delete('all')
        width = max(canvas.winfo_width(), 1)
        height = 30
        total = max(self.storage_info['total'], 1)
        used_ratio = min(self.storage_info['used'] / total, 1)
        used_segments = [0.34, 0.27, 0.22, 0.17]
        colors = ['#1677FF', '#22C55E', '#FF9F0A', '#FF453A']
        start = 0
        for portion, color in zip(used_segments, colors):
            end = start + int(width * used_ratio * portion)
            canvas.create_rectangle(start, 2, end, height, fill=color, outline='')
            start = end + 2
        canvas.create_rectangle(int(width * used_ratio), 2, width, height, fill='#D4D7DC', outline='')

    def add_dashboard_row(self, name, description, size, status='待扫描'):
        row = tk.Frame(self.result_container, bg='#FFFFFF', height=45)
        row.pack(fill='x')
        row.pack_propagate(False)
        for col, weight, minsize in ((0, 0, 72), (1, 0, 390), (2, 1, 0), (3, 0, 175)):
            row.grid_columnconfigure(col, weight=weight, minsize=minsize)
        symbol_map = {
            '临时文件': '⌫', 'Windows 更新清理': '↓', '浏览器缓存': '◎',
            '系统日志文件': '▤', '回收站': '◇', '缩略图缓存': '□', '错误报告文件': '⚙'
        }
        fields = (
            (0, '□', '#AEB4BC', 'center', ('Microsoft YaHei UI', 17)),
            (1, f"{symbol_map.get(name, '□')}    {name}", '#30343A', 'w', ('Microsoft YaHei UI', 12)),
            (2, description, '#5F6368', 'w', ('Microsoft YaHei UI', 11)),
            (3, size, '#4B4F55', 'e', ('Microsoft YaHei UI', 11)),
        )
        for col, text, foreground, anchor, font in fields:
            tk.Label(row, text=text, font=font, bg='#FFFFFF', fg=foreground, anchor=anchor).grid(row=0, column=col, sticky='nsew', padx=18)
        tk.Frame(row, bg='#E7E9ED', height=1).place(relx=0, rely=1, relwidth=1, anchor='sw')
        return
        row = tk.Frame(self.result_container, bg=COLORS['bg_card'], height=31)
        row.pack(fill='x')
        row.pack_propagate(False)
        for column, weight in enumerate((0, 2, 5, 0)):
            row.grid_columnconfigure(column, weight=weight)
        row.grid_columnconfigure(0, minsize=45)
        row.grid_columnconfigure(3, minsize=115)
        for column, text, foreground, anchor in [
            (0, '□', COLORS['text_muted'], 'center'), (1, name, COLORS['text_primary'], 'w'),
            (2, description, COLORS['text_muted'], 'w'), (3, size, COLORS['text_secondary'], 'e')
        ]:
            tk.Label(
                row, text=text, font=('Microsoft YaHei', 8), bg=COLORS['bg_card'],
                fg=foreground, anchor=anchor
            ).grid(row=0, column=column, sticky='nsew', padx=10)
        tk.Frame(row, bg=COLORS['border'], height=1).place(relx=0, rely=1, relwidth=1, anchor='sw')

    def render_dashboard_preview(self):
        for widget in self.result_container.winfo_children():
            widget.destroy()
        if getattr(self, 'dashboard_scan', False):
            preview_items = [
                ('临时文件', '系统和应用程序产生的临时文件', '2.45 GB'),
                ('Windows 更新清理', 'Windows 更新安装后的备份文件', '5.12 GB'),
                ('浏览器缓存', '浏览器缓存、Cookie 和历史记录等', '1.28 GB'),
                ('系统日志文件', '系统和应用程序日志文件', '356 MB'),
                ('回收站', '回收站中已删除的文件', '892 MB'),
                ('缩略图缓存', '系统缩略图缓存文件', '214 MB'),
                ('错误报告文件', '系统错误报告和崩溃转储文件', '128 MB'),
            ]
            for name, description, size in preview_items:
                self.add_dashboard_row(name, description, size)
            return
        preview_items = [
            ('临时文件', '系统和应用程序产生的临时文件', '待扫描'),
            ('Windows 更新清理', 'Windows 更新安装后的备份文件', '待扫描'),
            ('浏览器缓存', '浏览器缓存、Cookie 和历史记录等', '待扫描'),
            ('系统日志文件', '系统和应用程序日志文件', '待扫描'),
            ('回收站', '回收站中已删除的文件', '待扫描'),
            ('缩略图缓存', '系统缩略图缓存文件', '待扫描'),
            ('错误报告文件', '系统错误报告和崩溃转储文件', '待扫描'),
        ]
        for name, description, status in preview_items:
            self.add_dashboard_row(name, description, '--', status)

    def render_dashboard_results(self, cleaned=False):
        for widget in self.result_container.winfo_children():
            widget.destroy()
        for item in self.scan_results:
            description = '需要手动确认的文件夹' if item.get('manual') else '可安全清理的系统或应用缓存'
            self.add_dashboard_row(item['name'], description, format_size(item['size']), '已清理' if cleaned else '可清理')
        self.result_container.update_idletasks()
        self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))

    def show_dashboard_action(self, action):
        """Keep exactly one fixed-position primary action visible in the header."""
        if action == 'scan':
            self.clean_btn.place_forget()
            self.scan_btn.place(x=0, y=0, width=138, height=62)
        else:
            self.scan_btn.place_forget()
            self.clean_btn.place(x=0, y=0, width=138, height=62)

    def on_dashboard_scan_done(self):
        self.is_scanning = False
        self.scan_btn.config(state='normal', text='开始扫描')
        if self.scan_results:
            self.render_dashboard_results()
            self.cleanup_subtitle.config(text=f"已发现 {len(self.scan_results)} 项，可释放 {format_size(self.total_size)}。")
            self.clean_btn.config(state='normal', text='立即清理')
            self.show_dashboard_action('clean')
            self.recent_result.config(text=f"刚刚完成快速扫描，发现 {len(self.scan_results)} 项，可释放 {format_size(self.total_size)}")
        else:
            self.show_dashboard_action('scan')
            self.render_dashboard_preview()
            self.cleanup_subtitle.config(text='本次扫描未发现可清理文件。')
            self.recent_result.config(text='刚刚完成快速扫描，未发现可清理文件')
        self.update_disk_info()

    def create_optimize_tab(self):
        """创建系统优化标签页"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(tab, text="⚙️ 系统优化")

        # 标题行（带刷新按钮）
        title_frame = tk.Frame(tab, bg=COLORS['bg_primary'])
        title_frame.pack(fill='x', padx=20, pady=(20, 10))

        tk.Label(
            title_frame,
            text="系统优化面板",
            font=('Microsoft YaHei', 14, 'bold'),
            bg=COLORS['bg_primary'],
            fg=COLORS['text_primary']
        ).pack(side='left')

        refresh_btn = tk.Button(
            title_frame,
            text='🔄 刷新状态',
            font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'],
            relief='flat',
            padx=12,
            pady=4,
            cursor='hand2',
            command=self.refresh_optimize_status
        )
        refresh_btn.pack(side='right')

        # 滚动容器
        canvas = tk.Canvas(tab, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # 1. 网络凭据卡片
        self.create_optimize_card(
            scrollable_frame,
            '📡 网络凭据管理',
            '保存 \\192.168.0.44 网络共享凭据到 Windows 凭据管理器',
            'network',
            0
        )

        # 2. 系统备份卡片
        self.create_optimize_card(
            scrollable_frame,
            '💾 系统备份优化',
            '禁用 Windows 和 OpenClaw 自动备份,释放磁盘空间',
            'backup',
            1
        )

        canvas.pack(side='left', fill='both', expand=True, padx=(20, 0))
        scrollbar.pack(side='right', fill='y')

    def create_optimize_card(self, parent, title, description, card_type, index):
        """创建优化卡片"""
        card = tk.Frame(parent, bg=COLORS['bg_card'], bd=1, relief='solid')
        card.pack(fill='x', padx=0, pady=(0, 15))

        # 卡片标题
        tk.Label(
            card,
            text=title,
            font=('Microsoft YaHei', 12, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', padx=20, pady=(15, 5))

        # 卡片描述
        tk.Label(
            card,
            text=description,
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'],
            fg=COLORS['text_secondary'],
            justify='left'
        ).pack(anchor='w', padx=20, pady=(0, 15))

        # 功能列表
        if card_type == 'network':
            self.create_network_controls(card)
        elif card_type == 'backup':
            self.create_backup_controls(card)

        # 底部间距
        tk.Frame(card, bg=COLORS['bg_card'], height=15).pack(fill='x')

    def create_network_controls(self, parent):
        """创建网络凭据控制项"""
        # 状态显示
        status_frame = tk.Frame(parent, bg=COLORS['bg_card'])
        status_frame.pack(fill='x', padx=20, pady=(0, 10))

        tk.Label(
            status_frame,
            text="状态:",
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'],
            fg=COLORS['text_secondary']
        ).pack(side='left')

        self.network_status = tk.Label(
            status_frame,
            text="检查中...",
            font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_card'],
            fg=COLORS['warning']
        )
        self.network_status.pack(side='left', padx=(10, 0))

        # 操作按钮
        btn = tk.Button(
            parent,
            text="💾 保存网络凭据",
            font=('Microsoft YaHei', 10, 'bold'),
            bg=COLORS['gradient_start'],
            fg='white',
            activebackground=COLORS['gradient_end'],
            activeforeground='white',
            bd=0,
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.save_credentials
        )
        btn.pack(padx=20, pady=(0, 15), anchor='w')

    def create_backup_controls(self, parent):
        """创建备份控制项"""
        items = [
            ('Windows 备份', 'win_backup'),
            ('OpenClaw 备份', 'oc_backup')
        ]

        for label, key in items:
            frame = tk.Frame(parent, bg=COLORS['bg_card'])
            frame.pack(fill='x', padx=20, pady=(0, 10))

            tk.Label(
                frame,
                text=f"{label}:",
                font=('Microsoft YaHei', 9),
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']
            ).pack(side='left')

            status_label = tk.Label(
                frame,
                text="检查中...",
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['warning']
            )
            status_label.pack(side='left', padx=(10, 0))

            btn = tk.Button(
                frame,
                text="禁用",
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['danger'],
                fg='white',
                activebackground='#DC2626',
                activeforeground='white',
                bd=0,
                padx=15,
                pady=5,
                cursor='hand2'
            )
            btn.pack(side='right')

            # 保存引用
            if key == 'win_backup':
                self.win_backup_status = status_label
                self.win_backup_btn = btn
                btn.config(command=self.disable_win_backup)
            else:
                self.oc_backup_status = status_label
                self.oc_backup_btn = btn
                btn.config(command=self.disable_oc_backup)

    def refresh_optimize_status(self):
        """刷新系统优化状态"""
        # 网络凭据
        cred_ok = check_network_credentials()
        drive_ok = check_network_drive()
        if cred_ok and drive_ok:
            self.network_status.config(text="已保存 + Z盘已映射", fg=COLORS['success'])
        elif cred_ok:
            self.network_status.config(text="凭据已保存,Z盘未映射", fg=COLORS['warning'])
        else:
            self.network_status.config(text="未保存", fg=COLORS['danger'])

        # Windows 备份
        win_disabled = check_backup_status()
        if win_disabled:
            self.win_backup_status.config(text="已禁用", fg=COLORS['success'])
            self.win_backup_btn.config(text="已禁用", bg=COLORS['bg_secondary'], state='disabled')
        else:
            self.win_backup_status.config(text="未禁用", fg=COLORS['warning'])
            self.win_backup_btn.config(text="禁用", bg=COLORS['danger'], state='normal')

        # OpenClaw 备份
        oc_disabled = check_openclaw_backup_status()
        if oc_disabled:
            self.oc_backup_status.config(text="已禁用", fg=COLORS['success'])
            self.oc_backup_btn.config(text="已禁用", bg=COLORS['bg_secondary'], state='disabled')
        else:
            self.oc_backup_status.config(text="未禁用", fg=COLORS['warning'])
            self.oc_backup_btn.config(text="禁用", bg=COLORS['danger'], state='normal')

    def create_process_controls(self, parent):
        """创建进程管理控制项"""
        processes = [
            ('Codex', CODEX_NAMES, 'codex'),
            ('Google', GOOGLE_NAMES, 'google'),
            ('QClaw', QCLAW_NAMES, 'qclaw'),
            ('CC Switch', CC_SWITCH_NAMES, 'cc_switch'),
            ('Clash Verge', CLASH_VERGE_NAMES, 'clash_verge')
        ]

        for label, names, key in processes:
            frame = tk.Frame(parent, bg=COLORS['bg_card'])
            frame.pack(fill='x', padx=20, pady=(0, 10))

            tk.Label(
                frame,
                text=f"{label}:",
                font=('Microsoft YaHei', 9),
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']
            ).pack(side='left')

            status_label = tk.Label(
                frame,
                text="检查中...",
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['warning']
            )
            status_label.pack(side='left', padx=(10, 0))

            btn = tk.Button(
                frame,
                text="关闭",
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['danger'],
                fg='white',
                activebackground='#DC2626',
                activeforeground='white',
                bd=0,
                padx=15,
                pady=5,
                cursor='hand2'
            )
            btn.pack(side='right')

            # 保存引用
            setattr(self, f'{key}_status', status_label)
            setattr(self, f'{key}_btn', btn)

            # 绑定命令
            if key == 'codex':
                btn.config(command=self.kill_codex)
            elif key == 'google':
                btn.config(command=self.kill_google)
            elif key == 'qclaw':
                btn.config(command=self.kill_qclaw)
            elif key == 'cc_switch':
                btn.config(command=self.kill_cc_switch)
            elif key == 'clash_verge':
                btn.config(command=self.kill_clash_verge)

    def create_process_tab(self):
        """创建进程管理标签页"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(tab, text="进程管理")

        # 标题行
        title_frame = tk.Frame(tab, bg=COLORS['bg_primary'])
        title_frame.pack(fill='x', padx=20, pady=(20, 10))

        tk.Label(
            title_frame,
            text="一键关闭指定进程,释放系统资源",
            font=('Microsoft YaHei', 13, 'bold'),
            bg=COLORS['bg_primary'],
            fg=COLORS['text_primary']
        ).pack(side='left')

        refresh_btn = tk.Button(
            title_frame,
            text='🔄 刷新状态',
            font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'],
            relief='flat',
            padx=12,
            pady=4,
            cursor='hand2',
            command=self.check_all_processes
        )
        refresh_btn.pack(side='right')

        # 滚动容器
        canvas = tk.Canvas(tab, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        # 创建 canvas window,初始宽度设为 canvas 宽度
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')

        # 绑定 canvas 宽度变化,同步 scrollable_frame 宽度
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)

        # 进程卡片容器
        card_container = tk.Frame(scrollable_frame, bg=COLORS['bg_primary'])
        card_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # 定义所有进程
        processes = [
            ('Codex', CODEX_NAMES, 'codex', 'Codex AI 编程助手'),
            ('Google', GOOGLE_NAMES, 'google', 'Chrome 浏览器及相关服务'),
            ('QClaw', QCLAW_NAMES, 'qclaw', 'QClaw/OpenClaw 进程'),
            ('CC Switch', CC_SWITCH_NAMES, 'cc_switch', 'CCSwitch 网络代理工具'),
            ('Clash Verge', CLASH_VERGE_NAMES, 'clash_verge', 'Clash Verge 代理工具'),
        ]

        # 创建进程卡片 - 2列布局
        for i, (title, names, key, desc) in enumerate(processes):
            # 每行两个卡片
            row_frame = tk.Frame(card_container, bg=COLORS['bg_primary'])
            row_frame.pack(fill='x', pady=5)

            # 左卡片
            left_card = tk.Frame(
                row_frame,
                bg=COLORS['bg_card'],
                bd=1,
                relief='solid',
                height=100
            )
            left_card.pack(side='left', fill='both', expand=True, padx=(0, 5))
            left_card.pack_propagate(False)

            # 左卡片内容
            left_inner = tk.Frame(left_card, bg=COLORS['bg_card'])
            left_inner.pack(fill='both', expand=True, padx=15, pady=10)

            # 进程名称
            tk.Label(
                left_inner,
                text=title,
                font=('Microsoft YaHei', 13, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['text_primary'],
                anchor='w'
            ).pack(fill='x')

            # 描述
            tk.Label(
                left_inner,
                text=desc,
                font=('Microsoft YaHei', 8),
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary'],
                anchor='w'
            ).pack(fill='x')

            # 状态
            status_frame = tk.Frame(left_inner, bg=COLORS['bg_card'])
            status_frame.pack(fill='x', pady=5)

            tk.Label(
                status_frame,
                text="状态:",
                font=('Microsoft YaHei', 9),
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']
            ).pack(side='left')

            status_label = tk.Label(
                status_frame,
                text="检查中...",
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['warning']
            )
            status_label.pack(side='left', padx=(10, 0))

            # 保存引用
            setattr(self, f'{key}_status', status_label)

            # 右卡片(按钮)
            right_card = tk.Frame(
                row_frame,
                bg=COLORS['bg_card'],
                bd=1,
                relief='solid',
                width=120,
                height=100
            )
            right_card.pack(side='left', fill='y', padx=(5, 0))
            right_card.pack_propagate(False)

            # 按钮 - 根据进程类型绑定不同的命令
            btn = tk.Button(
                right_card,
                text="关闭进程",
                font=('Microsoft YaHei', 10, 'bold'),
                bg=COLORS['danger'],
                fg='white',
                activebackground='#DC2626',
                activeforeground='white',
                bd=0,
                cursor='hand2'
            )
            btn.pack(fill='both', expand=True, padx=10, pady=10)

            # 保存按钮引用
            setattr(self, f'{key}_btn', btn)

            # 根据进程类型绑定不同的命令
            if key == 'codex':
                btn.config(command=self.kill_codex)
            elif key == 'google':
                btn.config(command=self.kill_google)
            elif key == 'qclaw':
                btn.config(command=self.kill_qclaw)
            elif key == 'cc_switch':
                btn.config(command=self.kill_cc_switch)
            elif key == 'clash_verge':
                btn.config(command=self.kill_clash_verge)

        # 绑定滚动条
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def create_cloud_tab(self):
        """创建网盘挂载标签页"""
        self.create_dashboard_cloud_tab()

    def create_dashboard_cloud_tab(self):
        """Present the Quark mount using the same workbench visual system as the overview."""
        self.dashboard_cloud = True
        tab = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(tab, text="云端同步")
        tab.grid_columnconfigure(0, weight=1)

        header = tk.Frame(tab, bg=COLORS['bg_primary'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 16))
        tk.Label(
            header, text="云端同步", font=('Microsoft YaHei', 16, 'bold'),
            bg=COLORS['bg_primary'], fg=COLORS['text_primary']
        ).pack(side='left')
        self.quark_status_label = tk.Label(
            header, text="正在检查…", font=('Microsoft YaHei', 9),
            bg=COLORS['bg_primary'], fg=COLORS['text_muted']
        )
        self.quark_status_label.pack(side='right')

        card = tk.Frame(tab, bg=COLORS['bg_card'], bd=1, relief='solid')
        card.grid(row=1, column=0, sticky='ew')
        card.grid_columnconfigure(0, weight=1)
        card_inner = tk.Frame(card, bg=COLORS['bg_card'])
        card_inner.pack(fill='both', expand=True, padx=20, pady=18)

        title_row = tk.Frame(card_inner, bg=COLORS['bg_card'])
        title_row.pack(fill='x')
        tk.Label(title_row, text="夸克网盘", font=('Microsoft YaHei', 14, 'bold'), bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(side='left')
        self.quark_drive_badge = tk.Label(
            title_row, text="设备和驱动器  X:", font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_hover'], fg=COLORS['gradient_start'], padx=10, pady=4
        )
        self.quark_drive_badge.pack(side='right')
        tk.Label(
        card_inner, text="将夸克网盘显示为本机固定驱动器，可直接在资源管理器中访问和拖放文件。",
            font=('Microsoft YaHei', 9), bg=COLORS['bg_card'], fg=COLORS['text_muted']
        ).pack(anchor='w', pady=(7, 18))

        drive_row = tk.Frame(card_inner, bg=COLORS['bg_card'])
        drive_row.pack(fill='x', pady=(0, 16))
        tk.Label(
            drive_row, text='挂载盘符', font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'], fg=COLORS['text_muted']
        ).pack(side='left')
        self.quark_drive_var = tk.StringVar(value=QUARK_DEVICE_DRIVE)
        self.quark_drive_selector = ttk.Combobox(
            drive_row, textvariable=self.quark_drive_var,
            values=get_available_quark_drives(QUARK_DEVICE_DRIVE),
            state='readonly', width=7, font=('Microsoft YaHei', 10)
        )
        self.quark_drive_selector.pack(side='left', padx=(12, 10))
        self.quark_drive_selector.bind('<<ComboboxSelected>>', self.select_quark_device_drive)
        tk.Label(
            drive_row, text='选择后点击“重新挂载”生效，并会用于以后登录时自动挂载。',
            font=('Microsoft YaHei', 8), bg=COLORS['bg_card'], fg=COLORS['text_muted']
        ).pack(side='left')

        self.quark_mount_detail = tk.Label(
        card_inner, text="挂载源：本机夸克服务", font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'], fg=COLORS['text_secondary']
        )
        self.quark_mount_detail.pack(anchor='w')
        tk.Frame(card_inner, bg=COLORS['border'], height=1).pack(fill='x', pady=14)

        details = tk.Frame(card_inner, bg=COLORS['bg_card'])
        details.pack(fill='x')
        for title, value in [
            ('后端连接', '夸克本机服务'),
            ('本机设备盘', f'{QUARK_DEVICE_DRIVE}  夸克网盘'),
            ('登录后恢复', '自动恢复挂载'),
        ]:
            item = tk.Frame(details, bg=COLORS['bg_card'])
            item.pack(side='left', padx=(0, 54))
            tk.Label(item, text=title, font=('Microsoft YaHei', 8), bg=COLORS['bg_card'], fg=COLORS['text_muted']).pack(anchor='w')
            tk.Label(item, text=value, font=('Microsoft YaHei', 10, 'bold'), bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor='w', pady=(4, 0))

        actions = tk.Frame(tab, bg=COLORS['bg_primary'])
        actions.grid(row=2, column=0, sticky='ew', pady=(18, 0))
        tk.Button(
            actions, text="打开夸克网盘", font=('Microsoft YaHei', 10, 'bold'),
            bg=COLORS['gradient_start'], fg='white', activebackground=COLORS['gradient_end'],
            activeforeground='white', relief='flat', bd=0, padx=22, pady=8,
            cursor='hand2', command=self.open_quark_device_drive
        ).pack(side='right')
        tk.Button(
            actions, text="重新挂载", font=('Microsoft YaHei', 10),
            bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], activebackground=COLORS['bg_hover'],
            activeforeground=COLORS['text_primary'], relief='flat', bd=0, padx=20, pady=8,
            cursor='hand2', command=self.remount_quark_device_drive
        ).pack(side='right', padx=(0, 10))

        recent = tk.Frame(tab, bg=COLORS['bg_primary'])
        recent.grid(row=3, column=0, sticky='ew', pady=(28, 0))
        tk.Label(recent, text="挂载状态", font=('Microsoft YaHei', 11, 'bold'), bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(anchor='w', pady=(0, 7))
        status_table = tk.Frame(recent, bg=COLORS['bg_card'], bd=1, relief='solid')
        status_table.pack(fill='x')
        self.quark_last_check = tk.Label(
            status_table, text="正在读取本机驱动器状态…", font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'], fg=COLORS['text_muted'], anchor='w'
        )
        self.quark_last_check.pack(fill='x', padx=14, pady=10)
        self.root.after(100, self.refresh_cloud_status)

    def refresh_quark_device_status(self):
        device_ready = os.path.isdir(f'{QUARK_DEVICE_DRIVE}\\')
        backend_ready, backend_message = get_quark_backend_status()
        if device_ready:
            self.quark_status_label.config(text='● 已挂载，设备和驱动器可用', fg=COLORS['success'])
            self.quark_drive_badge.config(text=f'设备和驱动器  {QUARK_DEVICE_DRIVE}')
            self.quark_last_check.config(text=f'夸克网盘已挂载到 {QUARK_DEVICE_DRIVE}，已作为本机固定驱动器显示。')
        elif backend_ready:
            self.quark_status_label.config(text='● 夸克已连接，等待本机盘符', fg=COLORS['warning'])
            self.quark_last_check.config(text=f'夸克账号已连接，可点击“重新挂载”创建 {QUARK_DEVICE_DRIVE} 固定驱动器。')
        else:
            self.quark_status_label.config(text='● 等待夸克账号授权', fg=COLORS['danger'])
            self.quark_last_check.config(text=backend_message)

    def remount_quark_device_drive(self):
        stop_quark_device_mounts()
        time.sleep(1)
        success, message = ensure_quark_device_drive()
        self.refresh_quark_device_status()
        self.log(message, 'info' if success else 'error')
        if not success:
            messagebox.showerror('夸克网盘', message)

    def select_quark_device_drive(self, _event=None):
        """Persist the selected drive for the next explicit remount and future logons."""
        global QUARK_DEVICE_DRIVE
        selected_drive = self.quark_drive_var.get()
        try:
            QUARK_DEVICE_DRIVE = save_configured_quark_drive(selected_drive)
        except ValueError as error:
            messagebox.showerror('夸克网盘', str(error))
            self.quark_drive_var.set(QUARK_DEVICE_DRIVE)
            return
        self.quark_drive_badge.config(text=f'设备和驱动器  {QUARK_DEVICE_DRIVE}')
        self.quark_last_check.config(
            text=f'已保存 {QUARK_DEVICE_DRIVE}。点击“重新挂载”后切换，之后登录会自动使用该盘符。'
        )

    def open_quark_device_drive(self):
        success, message = ensure_quark_device_drive()
        self.refresh_quark_device_status()
        if not success:
            messagebox.showerror('夸克网盘', message)
            return
        os.startfile(f'{QUARK_DEVICE_DRIVE}\\')

    def mount_quark_drive(self):
        """挂载夸克网盘为本地驱动器"""
        mode = self.quark_mode_var.get()
        url = self.quark_url_entry.get().strip()
        username = self.quark_user_entry.get().strip()
        password = self.quark_pass_entry.get()
        drive = self.quark_drive_var.get()
        remember = self.quark_remember_var.get()

        # alist 模式特殊处理
        if mode == "alist":
            # 检查 alist 是否已安装
            alist_dir = os.path.expandvars(r'%USERPROFILE%\.alist')
            alist_exe = os.path.join(alist_dir, 'alist.exe')
            if not os.path.exists(alist_exe):
                messagebox.showwarning("提示", "alist 未安装,请先点击'下载安装 alist'按钮")
                return

            # 检查 alist 是否已启动
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', 5244))
                sock.close()
                if result != 0:
                    messagebox.showwarning("提示", "alist 未运行,请先点击'启动 alist'按钮")
                    return
            except:
                pass

            # alist 模式下使用默认配置
            if not url:
                url = "http://127.0.0.1:5244/dav"
            if not username:
                username = "admin"
            # alist 密码使用用户设置的密码 123456
            if not password:
                password = "123456"

        if not url:
            messagebox.showwarning("警告", "请输入 WebDAV 服务器地址")
            return
        if not username:
            messagebox.showwarning("警告", "请输入用户名或 Token")
            return

        self.log(f"开始挂载 {drive} → {url} ...")
        self.quark_status_label.config(text="挂载中...", fg=COLORS['warning'])
        self.quark_mount_btn.config(state='disabled', text="挂载中...")

        def do_mount():
            try:
                # 0. 检查并启动 WebClient 服务 (WebDAV 必需)
                self.root.after(0, lambda: self.log("检查 WebClient 服务..."))
                sc_result = subprocess.run(
                    ['sc', 'query', 'WebClient'],
                    capture_output=True, text=True, creationflags=0x08000000
                )
                if 'STOPPED' in sc_result.stdout and 'STOP_PENDING' not in sc_result.stdout:
                    self.root.after(0, lambda: self.log("WebClient 服务未启动,正在启动..."))
                    start_result = subprocess.run(
                        ['net', 'start', 'WebClient'],
                        capture_output=True, text=True, creationflags=0x08000000
                    )
                    if start_result.returncode == 0:
                        self.root.after(0, lambda: self.log("✓ WebClient 服务已启动"))
                    else:
                        self.root.after(0, lambda: self.log(f"启动 WebClient 失败: {start_result.stderr.strip()}", 'warn'))
                else:
                    self.root.after(0, lambda: self.log("✓ WebClient 服务已运行"))

                # 1. 如果需要记住凭据,先写入凭据管理器
                if remember and password:
                    # 先删除旧的凭据
                    subprocess.run(
                        ['cmdkey', '/delete:quark_webdav'],
                        capture_output=True, creationflags=0x08000000
                    )
                    # 添加新凭据
                    result = subprocess.run(
                        ['cmdkey', '/add:quark_webdav', f'/user:{username}', f'/pass:{password}'],
                        capture_output=True, text=True, creationflags=0x08000000
                    )
                    if result.returncode == 0:
                        self.root.after(0, lambda: self.log("✓ 凭据已保存到 Windows 凭据管理器"))

                # 2. 先尝试删除已存在的映射
                subprocess.run(
                    ['net', 'use', drive, '/delete', '/y'],
                    capture_output=True, creationflags=0x08000000
                )

                # 3. 使用 net use 挂载
                # Windows WebDAV 需要使用 UNC 格式: \\host@port\path
                # 将 http://127.0.0.1:5244/dav 转换为 \\127.0.0.1@5244\dav
                unc_path = url
                if url.startswith('http://'):
                    unc_path = url.replace('http://', '\\\\').replace(':', '@').replace('/', '\\')
                elif url.startswith('https://'):
                    unc_path = url.replace('https://', '\\\\').replace(':', '@').replace('/', '\\')

                self.root.after(0, lambda: self.log(f"执行: net use {drive} {unc_path}"))

                # 先保存凭据
                if password and username:
                    host_part = url.replace('http://', '').replace('https://', '').split('/')[0].split(':')[0]
                    subprocess.run(
                        ['cmdkey', '/add:' + host_part, '/user:' + username, '/pass:' + password],
                        capture_output=True, creationflags=0x08000000
                    )

                cmd = ['net', 'use', drive, unc_path]
                if password:
                    cmd.append(password)
                if username:
                    cmd.append(f'/user:{username}')

                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, creationflags=0x08000000
                )

                if result.returncode == 0:
                    self.root.after(0, lambda: self._on_mount_success(drive, url))
                else:
                    err_msg = result.stderr or result.stdout or "未知错误"
                    self.root.after(0, lambda: self._on_mount_failed(drive, err_msg))
            except Exception as e:
                self.root.after(0, lambda: self._on_mount_failed(drive, str(e)))

        threading.Thread(target=do_mount, daemon=True).start()

    def _mount_via_powershell(self, drive, url, username, password):
        """使用 PowerShell 挂载 WebDAV (备选方案)"""
        try:
            # 转义密码中的特殊字符
            ps_password = password.replace("'", "''")
            ps_username = username.replace("'", "''")

            ps_script = f"""
$ErrorActionPreference = 'Stop'
$secPwd = ConvertTo-SecureString '{ps_password}' -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential('{ps_username}', $secPwd)
# 删掉已存在的映射
net use {drive} /delete /y 2>$null | Out-Null
# 尝试 New-PSDrive 挂载
New-PSDrive -Name '{drive.Trim(':')}' -PSProvider FileSystem -Root '{url}' -Credential $cred -Persist -ErrorAction Stop
"""
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, creationflags=0x08000000,
                timeout=30
            )
            if result.returncode == 0:
                self.root.after(0, lambda: self.log(f"PowerShell 返回: {result.stdout.strip()}"))
                return True
            else:
                self.root.after(0, lambda: self.log(f"PowerShell 失败: {result.stderr.strip()}", 'error'))
                return False
        except Exception as e:
            self.root.after(0, lambda: self.log(f"PowerShell 异常: {str(e)}", 'error'))
            return False

    def _on_mount_success(self, drive, url):
        """挂载成功回调"""
        self.quark_status_label.config(text=f"已挂载 {drive}", fg=COLORS['success'])
        self.quark_mount_btn.config(state='normal', text="📥 挂载网盘")
        self.log(f"✓ 挂载成功: {drive} → {url}")
        messagebox.showinfo("成功", f"夸克网盘已挂载到 {drive}\n\n请打开资源管理器查看")

    def _on_mount_failed(self, drive, err_msg):
        """挂载失败回调"""
        self.quark_status_label.config(text="挂载失败", fg=COLORS['danger'])
        self.quark_mount_btn.config(state='normal', text="📥 挂载网盘")
        self.log(f"✗ 挂载失败: {err_msg.strip()}", 'error')
        messagebox.showerror("挂载失败", f"无法挂载 {drive}\n\n错误信息:\n{err_msg.strip()}\n\n请检查:\n1. WebDAV 地址是否正确\n2. Token/账号是否有效\n3. Windows WebClient 服务是否启动\n4. 网络连接是否正常")

    def unmount_quark_drive(self):
        """卸载夸克网盘"""
        drive = self.quark_drive_var.get()
        self.log(f"开始卸载 {drive} ...")

        def do_unmount():
            try:
                result = subprocess.run(
                    ['net', 'use', drive, '/delete', '/y'],
                    capture_output=True, text=True, creationflags=0x08000000
                )
                if result.returncode == 0:
                    self.root.after(0, lambda: self._on_unmount_success(drive))
                else:
                    err_msg = result.stderr or result.stdout or "未知错误"
                    self.root.after(0, lambda d=drive, e=err_msg: self._on_unmount_failed(d, e))
            except Exception as e:
                self.root.after(0, lambda d=drive, ex=str(e): self._on_unmount_failed(d, ex))

        threading.Thread(target=do_unmount, daemon=True).start()

    def _on_unmount_success(self, drive):
        """卸载成功回调"""
        self.quark_status_label.config(text="未挂载", fg=COLORS['text_muted'])
        self.log(f"✓ 已卸载 {drive}")
        messagebox.showinfo("成功", f"{drive} 已卸载")

    def _on_unmount_failed(self, drive, err_msg):
        """卸载失败回调"""
        self.log(f"✗ 卸载失败: {err_msg.strip()}", 'error')
        # 检查是否真的不存在
        if "找不到网络连接" in err_msg or "The network connection could not be found" in err_msg:
            self.quark_status_label.config(text="未挂载", fg=COLORS['text_muted'])
            messagebox.showinfo("提示", f"{drive} 未挂载,无需卸载")
        else:
            messagebox.showerror("卸载失败", f"无法卸载 {drive}\n\n{err_msg.strip()}")

    def _on_quark_mode_change(self):
        """夸克网盘模式切换回调"""
        mode = self.quark_mode_var.get()
        if mode == "alist":
            # 显示 alist 区域,隐藏 WebDAV 区域
            self.alist_frame.pack(fill='x', padx=15, pady=5)
            self.webdav_frame.pack_forget()
            self.quark_fetch_btn.pack_forget()
            self.remember_check.pack_forget()
            self.quark_desc_label.config(text="自动下载启动 alist,在网页配置夸克账号后即可挂载 (无需手动抓 Token)")
            self.help_text_label.config(text="""alist 一键配置流程:
1. 点击"下载安装 alist" (首次使用)
2. 点击"启动 alist" (每次开机后)
3. 点击"打开配置页面" → 在浏览器中配置夸克网盘
   - 点击"存储"→"添加"→选择"夸克"
   - 挂载路径填 "/夸克" (不要填其他内容)
   - Cookie 可通过"自动抓取 Cookie"按钮获取
   - 保存后回到本软件点击"挂载网盘"
4. 盘符默认 Q:,挂载后在资源管理器"此电脑"中访问""")
            # 自动填入 alist 默认地址
            self.quark_url_entry.delete(0, tk.END)
            self.quark_url_entry.insert(0, "http://127.0.0.1:5244/dav")
            self.quark_user_entry.delete(0, tk.END)
            self.quark_user_entry.insert(0, "admin")
        else:
            # 显示 WebDAV 区域,隐藏 alist 区域
            self.alist_frame.pack_forget()
            self.webdav_frame.pack(fill='x', padx=15, pady=5)
            self.quark_fetch_btn.pack(side='left', padx=(8, 0))
            self.remember_check.pack(side='left', padx=(20, 0))
            self.quark_desc_label.config(text="需要提供 WebDAV 服务器地址和认证 Token (Token 可从夸克网盘网页版 Cookie 中提取)")
            self.help_text_label.config(text="""WebDAV 直连模式:
1. 获取 Token: 登录夸克网盘网页版 → F12 → Network → Cookie 中找 '__puus=' 或 '__pus='
2. 点击"自动抓取 Cookie"可自动从浏览器提取
3. WebDAV 地址: 需使用第三方反代 (如 alist/rclone) 或自建服务
4. 盘符默认 Q:,挂载后在资源管理器中访问""")

    def check_alist_status(self):
        """检查 alist 安装和运行状态"""
        alist_dir = os.path.expandvars(r'%USERPROFILE%\.alist')
        alist_exe = os.path.join(alist_dir, 'alist.exe')

        if not os.path.exists(alist_exe):
            self.alist_status_label.config(text="未安装", fg=COLORS['text_muted'])
            self.alist_install_btn.config(state='normal')
            self.alist_start_btn.config(state='disabled')
            self.alist_config_btn.config(state='disabled')
            return

        # 检查是否在运行 (检测 5244 端口)
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 5244))
            sock.close()
            if result == 0:
                self.alist_status_label.config(text="运行中", fg=COLORS['success'])
                self.alist_install_btn.config(state='disabled')
                self.alist_start_btn.config(state='disabled')
                self.alist_config_btn.config(state='normal')
            else:
                self.alist_status_label.config(text="已安装,未运行", fg=COLORS['warning'])
                self.alist_install_btn.config(state='disabled')
                self.alist_start_btn.config(state='normal')
                self.alist_config_btn.config(state='disabled')
        except:
            self.alist_status_label.config(text="已安装", fg=COLORS['text_secondary'])

    def refresh_cloud_status(self):
        """刷新网盘状态"""
        if getattr(self, 'dashboard_cloud', False):
            self.refresh_quark_device_status()
            return
        try:
            # 检查 Q 盘是否已挂载
            result = subprocess.run(['net', 'use'], capture_output=True, text=True, creationflags=0x08000000)
            output = result.stdout
            mounted = False
            drive = self.quark_drive_var.get() if hasattr(self, 'quark_drive_var') else 'Q:'
            for line in output.split('\n'):
                if drive in line and ('\\127.0.0.1' in line or 'webdav' in line.lower() or '5244' in line or '\\RaiDrive' in line or '夸克' in line):
                    mounted = True
                    break

            if mounted:
                self.quark_status_label.config(text=f"已挂载 {drive}", fg=COLORS['success'])
            else:
                self.quark_status_label.config(text="未挂载", fg=COLORS['text_muted'])

            # 检查 alist 状态
            self.check_alist_status()

            self.log(f"✓ 网盘状态已刷新: {'已挂载' if mounted else '未挂载'}")
        except Exception as e:
            self.log(f"✗ 刷新网盘状态失败: {str(e)}", 'error')

    def install_alist(self):
        """下载并安装 alist"""
        self.alist_install_btn.config(state='disabled', text="下载中...")
        self.log("开始下载 alist...")

        def do_install():
            try:
                import urllib.request
                import zipfile

                alist_dir = os.path.expandvars(r'%USERPROFILE%\.alist')
                os.makedirs(alist_dir, exist_ok=True)

                # 下载 alist Windows 版 (v3.41.0)
                url = "https://github.com/AlistGo/alist/releases/download/v3.41.0/alist-windows-amd64.zip"
                zip_path = os.path.join(alist_dir, 'alist.zip')

                self.root.after(0, lambda: self.log(f"正在下载: {url}"))

                # 使用 urllib 下载
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=120) as response:
                    with open(zip_path, 'wb') as f:
                        f.write(response.read())

                self.root.after(0, lambda: self.log("下载完成,正在解压..."))

                # 解压
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(alist_dir)

                # 重命名为 alist.exe
                extracted_exe = os.path.join(alist_dir, 'alist-windows-amd64.exe')
                if os.path.exists(extracted_exe):
                    os.rename(extracted_exe, os.path.join(alist_dir, 'alist.exe'))

                # 删除 zip
                os.unlink(zip_path)

                self.root.after(0, lambda: self.log("✓ alist 安装完成"))
                self.root.after(0, self.check_alist_status)
                self.root.after(0, lambda: messagebox.showinfo("安装成功", "alist 已安装完成!\n\n请点击'启动 alist'按钮开始服务。"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"✗ alist 安装失败: {e}", 'error'))
                self.root.after(0, lambda: messagebox.showerror("安装失败", f"无法下载 alist:\n{e}\n\n请检查网络连接或手动下载:\nhttps://github.com/AlistGo/alist/releases"))
                self.root.after(0, self.check_alist_status)

        threading.Thread(target=do_install, daemon=True).start()

    def start_alist(self):
        """启动 alist 服务"""
        alist_dir = os.path.expandvars(r'%USERPROFILE%\.alist')
        alist_exe = os.path.join(alist_dir, 'alist.exe')

        if not os.path.exists(alist_exe):
            messagebox.showerror("错误", "alist 未安装,请先点击下载安装")
            return

        self.alist_start_btn.config(state='disabled', text="启动中...")
        self.log("正在启动 alist...")

        try:
            # 启动 alist server
            subprocess.Popen(
                [alist_exe, 'server'],
                cwd=alist_dir,
                creationflags=0x08000000  # 不显示控制台窗口
            )

            # 等待服务启动
            self.log("等待 alist 启动 (约 3 秒)...")
            self.root.after(3000, self._on_alist_started)
        except Exception as e:
            self.log(f"✗ 启动 alist 失败: {e}", 'error')
            self.alist_start_btn.config(state='normal', text="▶️ 启动 alist")

    def _on_alist_started(self):
        """alist 启动完成回调"""
        self.check_alist_status()
        if "运行中" in self.alist_status_label.cget("text"):
            self.log("✓ alist 已启动 (http://127.0.0.1:5244)")
            # 读取初始密码
            self._show_alist_password()
        else:
            self.log("✗ alist 启动失败,请检查端口 5244 是否被占用", 'error')
            self.alist_start_btn.config(state='normal', text="▶️ 启动 alist")

    def _show_alist_password(self):
        """显示 alist 初始密码"""
        alist_dir = os.path.expandvars(r'%USERPROFILE%\.alist')

        # 尝试从日志读取密码
        try:
            import glob
            log_files = glob.glob(os.path.join(alist_dir, 'log', 'log-*.log'))
            if log_files:
                latest_log = max(log_files, key=os.path.getctime)
                with open(latest_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'password is:' in line:
                            pwd = line.split('password is:')[-1].strip()
                            self.log(f"alist 初始密码: {pwd}")
                            messagebox.showinfo("alist 已启动",
                                f"alist 已成功启动!\n\n"
                                f"初始密码: {pwd}\n"
                                f"用户名: admin\n\n"
                                f"请点击'打开配置页面'进行夸克网盘配置。")
                            return
        except:
            pass

        messagebox.showinfo("alist 已启动",
            "alist 已成功启动!\n\n"
            "默认用户名: admin\n"
            "初始密码请查看命令行窗口或 alist 日志\n\n"
            "请点击'打开配置页面'进行配置。")

    def open_alist_config(self):
        """打开 alist 配置页面"""
        try:
            os.startfile("http://127.0.0.1:5244")
            self.log("已打开 alist 配置页面 (http://127.0.0.1:5244)")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开浏览器: {e}")

    def check_quark_status(self):
        """检查夸克网盘挂载状态"""
        drive = self.quark_drive_var.get()
        try:
            result = subprocess.run(
                ['net', 'use', drive],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if result.returncode == 0:
                self.quark_status_label.config(text=f"已挂载 {drive}", fg=COLORS['success'])
            else:
                self.quark_status_label.config(text="未挂载", fg=COLORS['text_muted'])
        except Exception:
            self.quark_status_label.config(text="未挂载", fg=COLORS['text_muted'])

    def open_drive(self, drive):
        """打开盘符"""
        try:
            os.startfile(drive)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开 {drive}\n{str(e)}")

    def fetch_quark_cookie(self):
        """从浏览器自动抓取夸克 Cookie"""
        self.quark_fetch_btn.config(state='disabled', text="抓取中...")
        self.log("开始从浏览器抓取夸克 Cookie...")
        self.quark_status_label.config(text="抓取中...", fg=COLORS['warning'])

        def do_fetch():
            results, errors = extract_quark_cookies_auto()
            self.root.after(0, lambda: self._on_fetch_done(results, errors))

        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_fetch_done(self, results, errors):
        """抓取 Cookie 完成回调"""
        self.quark_fetch_btn.config(state='normal', text="🔑 自动抓取 Cookie")

        if not results and not errors:
            messagebox.showwarning("未找到",
                "未在系统中的任何浏览器里找到夸克网盘 Cookie。\n\n"
                "请确认:\n"
                "1. 已在 Edge/Chrome 等浏览器登录 https://pan.quark.cn\n"
                "2. 浏览器已完全关闭(正在运行时会锁定数据库)\n"
                "3. 重新打开 DiskCleaner 重试")
            self.log("✗ 未找到任何夸克 Cookie", 'warn')
            self.quark_status_label.config(text="未找到", fg=COLORS['danger'])
            return

        # 显示抓取结果
        info_lines = []
        chosen = None  # (browser_key, cookies)
        for key, cookies in results.items():
            bname = BROWSER_DISPLAY_NAMES.get(key, key)
            info_lines.append(f"✓ {bname}:")
            for name, val in cookies.items():
                preview = val[:20] + '...' if len(val) > 20 else val
                info_lines.append(f"   {name} = {preview} (长度 {len(val)})")
            if not chosen:
                chosen = (key, cookies)

        if errors:
            for key, err in errors.items():
                bname = BROWSER_DISPLAY_NAMES.get(key, key)
                if key not in results:  # 只列未找到的
                    info_lines.append(f"✗ {bname}: {err}")

        # 自动填入第一个找到的浏览器
        if chosen:
            browser_key, cookies = chosen
            bname = BROWSER_DISPLAY_NAMES.get(browser_key, browser_key)
            username_val = cookies.get('__puus', cookies.get('__pus', ''))
            password_val = cookies.get('__pus', '')

            # 同时更新两个变量供用户选择
            self.quark_user_entry.delete(0, tk.END)
            self.quark_user_entry.insert(0, username_val)
            self.quark_pass_entry.delete(0, tk.END)
            self.quark_pass_entry.insert(0, password_val)
            # 默认勾选记住凭据
            self.quark_remember_var.set(True)

            self.log(f"✓ 已从 {bname} 抓取 Cookie (__puus 长度 {len(username_val)}, __pus 长度 {len(password_val)})", 'info')
            self.log(f"   用户名(Token)已填入: {username_val[:15]}...", 'info')
            self.log(f"   密码(Token)已填入: {password_val[:15]}...", 'info')
            self.quark_status_label.config(text=f"已抓取 ({bname})", fg=COLORS['success'])

            # 显示成功消息
            msg = "成功从以下浏览器抓取 Cookie 并填入:\n\n" + "\n".join(info_lines)
            if errors:
                msg += "\n\n其他浏览器:\n" + "\n".join([f"• {BROWSER_DISPLAY_NAMES.get(k, k)}: {e}" for k, e in errors.items()])
            msg += "\n\n已自动填入 用户名/Token 和 密码/Token。\n默认勾选了'记住凭据'。"
            messagebox.showinfo("抓取成功", msg)
        else:
            self.log("✗ 抓取失败: 未获取到任何 Cookie", 'error')
            self.quark_status_label.config(text="抓取失败", fg=COLORS['danger'])
            messagebox.showerror("抓取失败", "\n".join(info_lines))

    def create_status_bar(self):
        status_bar = tk.Frame(self.root, bg='#FFFFFF', height=55, highlightbackground='#E2E5EA', highlightthickness=1)
        status_bar.pack(fill='x', side='bottom')
        status_bar.pack_propagate(False)
        left = tk.Frame(status_bar, bg='#FFFFFF')
        left.pack(side='left', padx=27)
        tk.Label(left, text='●', font=('Microsoft YaHei UI', 19), bg='#FFFFFF', fg='#19C15A').pack(side='left')
        self.status_label = tk.Label(left, text='系统状态良好', font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#4B4F55')
        self.status_label.pack(side='left', padx=(10, 0))
        tk.Label(status_bar, text='上次扫描： 2024/05/19 10:32', font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#6B7078').pack(side='left', padx=122)
        tk.Label(status_bar, text='累计释放： 56.7 GB', font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#6B7078').pack(side='left', padx=55)
        tk.Label(status_bar, text='版本： 1.0.0.0', font=('Microsoft YaHei UI', 11), bg='#FFFFFF', fg='#6B7078').pack(side='right', padx=27)
        return
        """创建底部状态栏"""
        status_bar = tk.Frame(self.root, bg=COLORS['bg_secondary'], height=28)
        status_bar.pack(fill='x', side='bottom')
        status_bar.pack_propagate(False)

        left = tk.Frame(status_bar, bg=COLORS['bg_secondary'])
        left.pack(side='left', padx=18)
        tk.Label(left, text='●', font=('Microsoft YaHei', 9), bg=COLORS['bg_secondary'], fg=COLORS['success']).pack(side='left')
        self.status_label = tk.Label(
            left,
            text="系统状态良好",
            font=('Microsoft YaHei', 8),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_muted']
        )
        self.status_label.pack(side='left', padx=(6, 0))

        tk.Label(
            status_bar, text="上次扫描：--", font=('Microsoft YaHei', 8),
            bg=COLORS['bg_secondary'], fg=COLORS['text_muted']
        ).pack(side='left', padx=28)
        tk.Label(
            status_bar, text="累计释放：--", font=('Microsoft YaHei', 8),
            bg=COLORS['bg_secondary'], fg=COLORS['text_muted']
        ).pack(side='left', padx=28)
        tk.Label(
            status_bar, text="版本：1.0.0", font=('Microsoft YaHei', 8),
            bg=COLORS['bg_secondary'], fg=COLORS['text_muted']
        ).pack(side='right', padx=18)

    # ========== 功能方法 ==========

    def log(self, msg, level='info'):
        """添加日志"""
        ts = datetime.now().strftime("%H:%M:%S")
        tag = {'info': '[INFO]', 'warn': '[WARN]', 'error': '[ERROR]'}.get(level, '[INFO]')
        self.log_text.insert('end', f"[{ts}] {tag} {msg}\n")
        self.log_text.see('end')
        self.status_label.config(text=msg)

    def update_disk_info(self):
        """更新 C 盘信息"""
        info = get_disk_info()
        if info:
            if getattr(self, 'dashboard_scan', False):
                self.storage_info = info
                self.disk_percent.config(text=f"{info['percent']}%")
                self.disk_percent.config(fg=COLORS['text_primary'])
                self.disk_detail.config(text=f"已用：{format_size(info['used'])} / {format_size(info['total'])}")
                self.disk_free_label.config(text=f"可用：{format_size(info['free'])}")
                self.draw_storage_bar()
                return
            self.disk_percent.config(text=f"{info['percent']}%")
            color = COLORS['success'] if info['percent'] < 70 else (COLORS['warning'] if info['percent'] < 90 else COLORS['danger'])
            self.disk_percent.config(fg=color)
            self.disk_detail.config(text=f"{format_size(info['free'])} 可用 / {format_size(info['total'])} 总共")

    def start_scan(self):
        """开始扫描"""
        if self.is_scanning:
            return
        self.is_scanning = True
        if getattr(self, 'dashboard_scan', False):
            self.show_dashboard_action('scan')
        self.scan_btn.config(state='disabled', text="扫描中...")
        self.clean_btn.config(state='disabled')
        self.log("开始扫描 C 盘垃圾文件...")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        """执行扫描"""
        self.scan_results = []
        self.total_size = 0
        paths = get_paths_to_clean()

        # 记录扫描路径数量
        self.root.after(0, lambda: self.log(f"发现 {len(paths)} 个待扫描路径"))

        for item in paths:
            path = item['path']
            name = item['name']
            self.root.after(0, lambda n=name: self.log(f"  扫描中: {n}..."))

            if os.path.exists(path):
                try:
                    size = fast_scan_size(path)
                    if size > 0:
                        self.scan_results.append({**item, 'size': size})
                        self.total_size += size
                        self.root.after(0, lambda n=name, s=size: self.log(f"  ✓ {n}: {format_size(s)}"))
                    else:
                        self.root.after(0, lambda n=name: self.log(f"  - {n}: 为空或无法访问", 'warn'))
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda n=name, e=error_msg: self.log(f"  ✗ {n}: 扫描失败 - {e}", 'error'))
            else:
                self.root.after(0, lambda n=name: self.log(f"  - {n}: 路径不存在", 'warn'))

        self.root.after(0, self._on_scan_done)

    def _on_scan_done(self):
        """扫描完成"""
        if getattr(self, 'dashboard_scan', False):
            self.on_dashboard_scan_done()
            return
        self.is_scanning = False
        self.scan_btn.config(state='normal', text="开始扫描")

        # 清空之前的结果
        for widget in self.result_container.winfo_children():
            widget.destroy()

        if self.scan_results:
            # 统计自动清理和手动清理的数量
            auto_count = sum(1 for r in self.scan_results if not r.get('manual', False))
            manual_count = sum(1 for r in self.scan_results if r.get('manual', False))
            auto_size = sum(r['size'] for r in self.scan_results if not r.get('manual', False))

            # 显示扫描结果列表
            for i, item in enumerate(self.scan_results):
                is_manual = item.get('manual', False)

                row_frame = tk.Frame(self.result_container, bg=COLORS['bg_card'], height=30)
                row_frame.pack(fill='x', pady=1)
                row_frame.pack_propagate(False)

                # 使用 grid 布局
                row_frame.grid_columnconfigure(0, weight=3)  # 名称
                row_frame.grid_columnconfigure(1, weight=2)  # 大小
                row_frame.grid_columnconfigure(2, weight=1)  # 状态/操作

                # 项目名称
                tk.Label(
                    row_frame,
                    text=item['name'],
                    font=('Microsoft YaHei', 9),
                    bg=COLORS['bg_card'],
                    fg=COLORS['text_primary'],
                    anchor='w'
                ).grid(row=0, column=0, sticky='w', padx=10, pady=5)

                # 大小
                tk.Label(
                    row_frame,
                    text=format_size(item['size']),
                    font=('Microsoft YaHei', 9, 'bold'),
                    bg=COLORS['bg_card'],
                    fg=COLORS['gradient_start'],
                    anchor='w'
                ).grid(row=0, column=1, sticky='w', padx=10, pady=5)

                # 状态或操作按钮
                if is_manual:
                    # 手动删除项:显示"手动删除"标签 + 打开文件夹按钮
                    btn = tk.Button(
                        row_frame,
                        text="打开文件夹",
                        font=('Microsoft YaHei', 8, 'bold'),
                        bg='#F97316',  # 橙色
                        fg='white',
                        activebackground='#EA580C',
                        activeforeground='white',
                        bd=0,
                        padx=8,
                        pady=2,
                        cursor='hand2',
                        command=lambda p=item['path']: self.open_folder(p)
                    )
                    btn.grid(row=0, column=2, sticky='w', padx=10, pady=3)
                else:
                    # 自动清理项:显示"待清理"状态
                    tk.Label(
                        row_frame,
                        text="待清理",
                        font=('Microsoft YaHei', 9),
                        bg=COLORS['bg_card'],
                        fg=COLORS['warning'],
                        anchor='w'
                    ).grid(row=0, column=2, sticky='w', padx=10, pady=5)

            # 更新滚动区域以包含所有项目
            self.result_container.update_idletasks()
            self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))

            # 更新统计信息
            if manual_count > 0:
                self.scan_stats.config(text=f"{len(self.scan_results)} 项\n{format_size(self.total_size)}\n(含{manual_count}项手动)")
            else:
                self.scan_stats.config(text=f"{len(self.scan_results)} 项\n{format_size(self.total_size)}")

            self.clean_btn.config(state='normal')
            self.log(f"扫描完成: 发现 {len(self.scan_results)} 项 ({auto_count}项自动 + {manual_count}项手动),共 {format_size(self.total_size)}")
        else:
            # 无结果时显示提示
            tk.Label(
                self.result_container,
                text="未发现垃圾文件",
                font=('Microsoft YaHei', 10),
                bg=COLORS['bg_card'],
                fg=COLORS['text_muted']
            ).pack(pady=50)

            self.result_container.update_idletasks()
            self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all'))

            self.scan_stats.config(text="未发现垃圾文件")
            self.log("扫描完成: 未发现垃圾文件")

        self.update_disk_info()

    def open_folder(self, path):
        """打开文件夹"""
        try:
            if os.path.exists(path):
                os.startfile(path)
                self.log(f"已打开文件夹: {path}")
            else:
                messagebox.showwarning("警告", f"路径不存在:\n{path}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹:\n{str(e)}")

    def start_clean(self):
        """开始清理"""
        if not self.scan_results:
            return
        if self.is_cleaning:
            return
        self.is_cleaning = True
        if getattr(self, 'dashboard_scan', False):
            self.show_dashboard_action('clean')
        self.scan_btn.config(state='disabled')
        self.clean_btn.config(state='disabled', text="清理中...")
        self.log(f"开始清理 {len(self.scan_results)} 项垃圾文件...")
        threading.Thread(target=self._do_clean, daemon=True).start()

    def _do_clean(self):
        """执行清理"""
        total = 0
        cleaned_count = 0
        skipped_manual = 0

        for i, item in enumerate(self.scan_results):
            name = item['name']
            path = item['path']
            is_manual = item.get('manual', False)

            if is_manual:
                # 跳过手动删除项
                self.root.after(0, lambda n=name: self.log(f"跳过(手动): {n}"))
                skipped_manual += 1
                continue

            self.root.after(0, lambda n=name: self.log(f"正在清理: {n}..."))

            # 清理目录(30秒超时)
            c, s, errors = clear_directory(path, timeout=30)
            total += s
            cleaned_count += 1

            progress = (i + 1) / len(self.scan_results) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))

            if errors:
                self.root.after(0, lambda e=errors: self.log(f"清理警告: {', '.join(e)}", 'warn'))

        self.root.after(0, lambda t=total, c=cleaned_count, s=skipped_manual: self._on_clean_done(t, c, s))

    def _on_clean_done(self, total, cleaned_count=0, skipped_manual=0):
        """清理完成"""
        if getattr(self, 'dashboard_scan', False):
            self.is_cleaning = False
            self.show_dashboard_action('scan')
            self.scan_btn.config(state='normal', text='开始扫描')
            self.progress_var.set(100)
            self.render_dashboard_results(cleaned=True)
            self.cleanup_subtitle.config(text=f"清理完成，已释放 {format_size(total)} 磁盘空间。")
            self.recent_result.config(text=f"刚刚完成清理，已释放 {format_size(total)}")
            self.log(f"清理完成! 共释放 {format_size(total)} 磁盘空间 ({cleaned_count}项)")
            self.update_disk_info()
            return
        self.is_cleaning = False
        self.clean_btn.config(state='disabled', text="立即清理")
        self.scan_btn.config(state='normal', text="开始扫描")
        self.clean_stats.config(text=f"释放 {format_size(total)}")
        self.progress_var.set(100)

        # 更新列表中所有项目的状态
        for widget in self.result_container.winfo_children():
            # 查找状态标签(第3列的Label或Button)
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) and child.cget('text') == "待清理":
                    child.config(text="已清理", fg=COLORS['success'])

        # 构建日志消息
        log_msg = f"清理完成! 共释放 {format_size(total)} 磁盘空间 ({cleaned_count}项)"
        if skipped_manual > 0:
            log_msg += f", 跳过{skipped_manual}项手动删除"
        self.log(log_msg)
        self.update_disk_info()

    def check_system_status(self):
        """检查系统状态"""
        # 网络凭据
        cred_ok = check_network_credentials()
        drive_ok = check_network_drive()
        if cred_ok and drive_ok:
            self.network_status.config(text="已保存 + Z盘已映射", fg=COLORS['success'])
        elif cred_ok:
            self.network_status.config(text="凭据已保存,Z盘未映射", fg=COLORS['warning'])
        else:
            self.network_status.config(text="未保存", fg=COLORS['warning'])

        # 备份状态
        if check_backup_status():
            self.win_backup_status.config(text="已禁用", fg=COLORS['success'])
            self.win_backup_btn.config(text="已禁用", bg=COLORS['bg_secondary'], state='disabled')

        if check_openclaw_backup_status():
            self.oc_backup_status.config(text="已禁用", fg=COLORS['success'])
            self.oc_backup_btn.config(text="已禁用", bg=COLORS['bg_secondary'], state='disabled')

        # 进程状态
        self.check_all_processes()

        # 更新磁盘信息
        self.update_disk_info()

    def check_all_processes(self):
        """检查所有进程状态"""
        # Codex
        procs = get_processes_by_names(CODEX_NAMES)
        if procs:
            self.codex_status.config(text=f"运行中 ({len(procs)})", fg=COLORS['warning'])
            self.codex_btn.config(bg=COLORS['danger'], state='normal')
        else:
            self.codex_status.config(text="未运行", fg=COLORS['success'])
            self.codex_btn.config(bg=COLORS['bg_secondary'], state='disabled')

        # Google
        procs = get_processes_by_names(GOOGLE_NAMES)
        if procs:
            self.google_status.config(text=f"运行中 ({len(procs)})", fg=COLORS['warning'])
            self.google_btn.config(bg=COLORS['danger'], state='normal')
        else:
            self.google_status.config(text="未运行", fg=COLORS['success'])
            self.google_btn.config(bg=COLORS['bg_secondary'], state='disabled')

        # QClaw
        procs = get_processes_by_names(QCLAW_NAMES)
        if procs:
            self.qclaw_status.config(text=f"运行中 ({len(procs)})", fg=COLORS['warning'])
            self.qclaw_btn.config(bg=COLORS['danger'], state='normal')
        else:
            self.qclaw_status.config(text="未运行", fg=COLORS['success'])
            self.qclaw_btn.config(bg=COLORS['bg_secondary'], state='disabled')

        # CC Switch
        procs = get_processes_by_names(CC_SWITCH_NAMES)
        if procs:
            self.cc_switch_status.config(text=f"运行中 ({len(procs)})", fg=COLORS['warning'])
            self.cc_switch_btn.config(bg=COLORS['danger'], state='normal')
        else:
            self.cc_switch_status.config(text="未运行", fg=COLORS['success'])
            self.cc_switch_btn.config(bg=COLORS['bg_secondary'], state='disabled')

        # Clash Verge
        procs = get_processes_by_names(CLASH_VERGE_NAMES)
        if procs:
            self.clash_verge_status.config(text=f"运行中 ({len(procs)})", fg=COLORS['warning'])
            self.clash_verge_btn.config(bg=COLORS['danger'], state='normal')
        else:
            self.clash_verge_status.config(text="未运行", fg=COLORS['success'])
            self.clash_verge_btn.config(bg=COLORS['bg_secondary'], state='disabled')

    def save_credentials(self):
        """保存网络凭据"""
        self.log("保存网络凭据...")
        success, msg = save_network_credentials()
        if success:
            messagebox.showinfo("成功", msg)
            self.check_system_status()
        else:
            messagebox.showerror("失败", msg)

    def disable_win_backup(self):
        """禁用 Windows 备份"""
        if not messagebox.askyesno("确认", "确定要禁用 Windows 自动备份吗?"):
            return
        self.log("禁用 Windows 自动备份...")
        results = disable_auto_backup()
        for r in results:
            print(r)
        self.check_system_status()
        messagebox.showinfo("完成", "已禁用 Windows 自动备份!")

    def disable_oc_backup(self):
        """禁用 OpenClaw 备份"""
        if not messagebox.askyesno("确认", "确定要禁用 OpenClaw 自动备份吗?"):
            return
        self.log("禁用 OpenClaw 自动备份...")
        results, ok = disable_openclaw_backup()
        for r in results:
            print(r)
        self.check_system_status()
        messagebox.showinfo("完成", "已禁用 OpenClaw 自动备份!")

    def kill_codex(self):
        """关闭 Codex 进程"""
        self._kill_process('Codex', CODEX_NAMES)

    def kill_google(self):
        """关闭 Google 进程"""
        self._kill_process('Google', GOOGLE_NAMES)

    def kill_qclaw(self):
        """关闭 QClaw 进程"""
        self._kill_process('QClaw', QCLAW_NAMES)

    def kill_cc_switch(self):
        """关闭 CC Switch 进程"""
        self._kill_process('CC Switch', CC_SWITCH_NAMES)

    def kill_clash_verge(self):
        """关闭 Clash Verge 进程"""
        self._kill_process('Clash Verge', CLASH_VERGE_NAMES)

    def _kill_process(self, name, proc_names):
        """通用进程关闭方法"""
        if not messagebox.askyesno("确认", f"确定要关闭所有 {name} 进程吗?"):
            return
        self.log(f"关闭 {name} 进程...")
        results, ok = kill_processes_by_names(proc_names)
        for r in results:
            print(r)
        self.check_all_processes()
        if ok:
            messagebox.showinfo("完成", "\n".join(results))
        else:
            messagebox.showinfo("提示", f"未找到运行中的 {name} 进程")

# ========== 主程序入口 ==========

    def create_launcher_tab(self):
        """创建软件启动标签页"""
        tab = tk.Frame(self.notebook, bg=COLORS['bg_primary'])
        self.notebook.add(tab, text="🚀 软件启动")

        # 滚动容器
        canvas = tk.Canvas(tab, bg=COLORS['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg_primary'])

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # ======= 账户权限检查 =======
        current_user = get_current_username()
        if not is_admin_allowed():
            # 显示权限禁止界面
            forbid_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_card'], bd=1, relief='solid')
            forbid_frame.pack(fill='x', padx=20, pady=(30, 10))

            forbid_inner = tk.Frame(forbid_frame, bg=COLORS['bg_card'])
            forbid_inner.pack(padx=30, pady=25)

            tk.Label(
                forbid_inner,
                text='🔒',
                font=('Segoe UI Emoji', 48),
                bg=COLORS['bg_card']
            ).pack(pady=(0, 15))

            tk.Label(
                forbid_inner,
                text='权限不足',
                font=('Microsoft YaHei', 18, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['danger']
            ).pack()

            tk.Label(
                forbid_inner,
                text=f'当前账户: {current_user}',
                font=('Microsoft YaHei', 10),
                bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']
            ).pack(pady=(8, 0))

            tk.Label(
                forbid_inner,
                text=f'该功能仅限 [{ALLOWED_USER}] 账户使用',
                font=('Microsoft YaHei', 10),
                bg=COLORS['bg_card'],
                fg=COLORS['warning']
            ).pack(pady=(5, 15))

            return  # 不再加载软件列表

        # ======= 正常模式 =======
        # 标题行（包含刷新按钮）
        title_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_primary'])
        title_frame.pack(fill='x', pady=(20, 5), padx=20)

        title_label = tk.Label(
            title_frame,
            text="🚀 快速启动常用软件",
            font=('Microsoft YaHei', 14, 'bold'),
            bg=COLORS['bg_primary'],
            fg=COLORS['text_primary']
        )
        title_label.pack(side='left')

        # 顶部刷新全部状态按钮
        refresh_all_btn = tk.Button(
            title_frame,
            text='🔄 刷新全部状态',
            font=('Microsoft YaHei', 9, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'],
            relief='flat',
            padx=12,
            pady=4,
            cursor='hand2',
            command=self.refresh_launcher_cards
        )
        refresh_all_btn.pack(side='right')

        # 副标题（显示当前账户）
        sub_label = tk.Label(
            scrollable_frame,
            text=f"点击卡片即可启动软件 · 可自由添加和删除   [当前: {current_user}]",
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_primary'],
            fg=COLORS['text_secondary']
        )
        sub_label.pack(pady=(0, 15), padx=20, anchor='w')

        # 加载软件列表
        self.launcher_software = load_software_list()

        # 软件卡片容器
        self.launcher_cards_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_primary'])
        self.launcher_cards_frame.pack(fill='x', padx=15, pady=5)

        # 刷新软件卡片
        self.refresh_launcher_cards()

        # 底部按钮栏
        btn_frame = tk.Frame(scrollable_frame, bg=COLORS['bg_primary'])
        btn_frame.pack(fill='x', padx=20, pady=15)

        # 添加按钮
        add_btn = tk.Button(
            btn_frame,
            text='➕ 添加软件',
            font=('Microsoft YaHei', 10),
            bg='#6366F1',
            fg='white',
            relief='flat',
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.show_add_software_dialog
        )
        add_btn.pack(side='left')

        # 刷新全部状态
        refresh_btn_bottom = tk.Button(
            btn_frame,
            text='🔄 刷新状态',
            font=('Microsoft YaHei', 10),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'],
            relief='flat',
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.refresh_launcher_cards
        )
        refresh_btn_bottom.pack(side='left', padx=10)

        # 一键启动全部按钮
        launch_all_btn = tk.Button(
            btn_frame,
            text='🚀 全部启动',
            font=('Microsoft YaHei', 10),
            bg='#10B981',
            fg='white',
            relief='flat',
            padx=20,
            pady=8,
            cursor='hand2',
            command=self.launch_all_software
        )
        launch_all_btn.pack(side='left', padx=10)

    def refresh_launcher_cards(self):
        """刷新软件卡片列表"""
        # 清空旧卡片
        for widget in self.launcher_cards_frame.winfo_children():
            widget.destroy()

        # 每行4个
        row = None
        for i, software in enumerate(self.launcher_software):
            if i % 4 == 0:
                row = tk.Frame(self.launcher_cards_frame, bg=COLORS['bg_primary'])
                row.pack(fill='x', pady=5)

            card = tk.Frame(
                row,
                bg=COLORS['bg_card'],
                bd=1,
                relief='solid',
                cursor='hand2',
                width=200,
                height=130
            )
            card.pack(side='left', padx=6, ipadx=0, ipady=0)
            card.pack_propagate(False)

            # 顶部颜色条
            color_bar = tk.Frame(card, bg=software.get('color', '#6366F1'), height=4)
            color_bar.pack(fill='x')

            # 内部布局
            inner = tk.Frame(card, bg=COLORS['bg_card'])
            inner.pack(fill='both', expand=True, padx=10, pady=8)

            # ======= Logo + 名称 行 =======
            top_row = tk.Frame(inner, bg=COLORS['bg_card'])
            top_row.pack(fill='x')

            # 绘制Logo
            logo = draw_software_logo(top_row, software, size=48)
            logo.pack(side='left', padx=(0, 10))

            # 名称和状态
            info_col = tk.Frame(top_row, bg=COLORS['bg_card'])
            info_col.pack(side='left', fill='y', expand=True)

            name_lbl = tk.Label(
                info_col,
                text=software.get('name', '未知'),
                font=('Microsoft YaHei', 10, 'bold'),
                bg=COLORS['bg_card'],
                fg=COLORS['text_primary'],
                anchor='w'
            )
            name_lbl.pack(anchor='w')

            # 运行状态
            is_running = check_software_running(software)
            status_color = COLORS['warning'] if is_running else COLORS['text_muted']
            status_text = '● 运行中' if is_running else '○ 未运行'
            status_lbl = tk.Label(
                info_col,
                text=status_text,
                font=('Microsoft YaHei', 8),
                bg=COLORS['bg_card'],
                fg=status_color
            )
            status_lbl.pack(anchor='w', pady=(2, 0))

            # ======= 按钮行 =======
            btn_row = tk.Frame(inner, bg=COLORS['bg_card'])
            btn_row.pack(fill='x', pady=(6, 0))

            # 启动按钮
            launch_btn = tk.Button(
                btn_row,
                text='▶ 启动',
                font=('Microsoft YaHei', 8, 'bold'),
                bg='#10B981' if not is_running else '#F59E0B',
                fg='white',
                relief='flat',
                padx=10,
                pady=3,
                cursor='hand2',
                command=lambda s=software: self.launch_single_software(s)
            )
            launch_btn.pack(side='left')

            # 刷新按钮
            refresh_btn = tk.Button(
                btn_row,
                text='🔄 刷新',
                font=('Microsoft YaHei', 8),
                bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary'],
                relief='flat',
                padx=8,
                pady=3,
                cursor='hand2',
                command=lambda: self.refresh_launcher_cards()
            )
            refresh_btn.pack(side='left', padx=(4, 0))

            # 删除按钮
            del_btn = tk.Button(
                btn_row,
                text='✕',
                font=('Microsoft YaHei', 9, 'bold'),
                bg=COLORS['bg_secondary'],
                fg=COLORS['text_muted'],
                relief='flat',
                width=3,
                pady=3,
                cursor='hand2',
                command=lambda s=software: self.remove_software(s)
            )
            del_btn.pack(side='right')

            # 路径显示（hover提示）
            path_lbl = tk.Label(
                inner,
                text=software.get('path', ''),
                font=('Microsoft YaHei', 7),
                bg=COLORS['bg_card'],
                fg=COLORS['text_muted'],
                anchor='w'
            )
            path_lbl.pack(fill='x', pady=(4, 0))

    def launch_single_software(self, software):
        """启动单个软件"""
        success, msg = launch_software(software)
        if success:
            self.log(msg)
            # 延迟刷新状态
            self.root.after(1500, self.refresh_launcher_cards)
        else:
            messagebox.showwarning('启动失败', f"无法启动 {software.get('name', '未知')}\n\n{msg}")

    def launch_all_software(self):
        """一键启动全部软件"""
        if not is_admin_allowed():
            messagebox.showwarning(
                '权限不足',
                f'🔒 该功能仅限 [{ALLOWED_USER}] 账户使用\n\n'
                f'当前账户: {get_current_username()}'
            )
            return
        started = []
        failed = []
        for software in self.launcher_software:
            success, msg = launch_software(software)
            if success:
                started.append(software.get('name', '未知'))
            else:
                failed.append(f"{software.get('name', '未知')}: {msg}")

        if started:
            self.log(f'已启动 {len(started)} 个软件: {" · ".join(started)}')
        if failed:
            msg = f"启动成功 {len(started)} 个，失败 {len(failed)} 个:\n" + '\n'.join(failed)
            messagebox.showwarning('部分启动失败', msg)
        elif not started:
            messagebox.showwarning('未启动任何软件', '未找到任何可启动的软件')

        self.root.after(1500, self.refresh_launcher_cards)

    def remove_software(self, software):
        """删除软件"""
        name = software.get('name', '未知')
        if messagebox.askyesno('确认删除', f'确定要从列表中删除 "{name}" 吗？\n\n（不会卸载软件，仅从列表移除）'):
            self.launcher_software = [s for s in self.launcher_software if s.get('name') != name]
            save_software_list(self.launcher_software)
            self.refresh_launcher_cards()
            self.log(f'已删除软件: {name}')

    def show_add_software_dialog(self):
        """显示添加软件对话框（仅限 Administrator 账户）"""
        if not is_admin_allowed():
            messagebox.showwarning(
                '权限不足',
                f'🔒 该功能仅限 [{ALLOWED_USER}] 账户使用\n\n'
                f'当前账户: {get_current_username()}'
            )
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('添加软件')
        dialog.geometry('480x380')
        dialog.configure(bg=COLORS['bg_secondary'])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 190
        dialog.geometry(f'480x380+{x}+{y}')

        # 标题
        tk.Label(
            dialog,
            text='添加新软件到启动器',
            font=('Microsoft YaHei', 13, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary']
        ).pack(pady=(20, 15))

        # 输入区域
        input_frame = tk.Frame(dialog, bg=COLORS['bg_secondary'])
        input_frame.pack(fill='x', padx=30)

        fields = [
            ('软件名称:', 'name_entry'),
            ('可执行文件路径:', 'path_entry'),
            ('图标 (emoji):', 'icon_entry'),
            ('颜色代码:', 'color_entry'),
        ]

        entries = {}
        defaults = [
            '',  # name
            '',  # path
            '📦',  # icon
            '#6366F1',  # color
        ]

        for idx, (label, key) in enumerate(fields):
            row = tk.Frame(input_frame, bg=COLORS['bg_secondary'])
            row.pack(fill='x', pady=6)

            tk.Label(
                row,
                text=label,
                font=('Microsoft YaHei', 9),
                bg=COLORS['bg_secondary'],
                fg=COLORS['text_secondary'],
                width=14,
                anchor='w'
            ).pack(side='left')

            entry = tk.Entry(row, font=('Microsoft YaHei', 10), width=30)
            entry.pack(side='left', fill='x', expand=True)
            entry.insert(0, defaults[idx])
            entries[key] = entry

        # 浏览按钮
        browse_row = tk.Frame(input_frame, bg=COLORS['bg_secondary'])
        browse_row.pack(fill='x', pady=6)

        tk.Label(
            browse_row,
            text='可执行文件路径:',
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary'],
            width=14,
            anchor='w'
        ).pack(side='left')

        path_entry_wrapper = tk.Frame(browse_row, bg=COLORS['bg_secondary'])
        path_entry_wrapper.pack(side='left', fill='x', expand=True)
        entries['path_entry'].pack_forget()
        entries['path_entry'].pack(side='left', fill='x', expand=True)

        def browse_file():
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                title='选择可执行文件',
                filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')],
                initialdir='C:\\Program Files'
            )
            if filename:
                entries['path_entry'].delete(0, tk.END)
                entries['path_entry'].insert(0, filename)
                # 自动提取文件名作为名称
                if not entries['name_entry'].get():
                    import ntpath
                    name = ntpath.basename(filename)
                    name = name.replace('.exe', '').replace('.EXE', '')
                    entries['name_entry'].insert(0, name)

        tk.Button(
            browse_row,
            text='浏览...',
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_card'],
            fg=COLORS['text_primary'],
            relief='solid',
            padx=10,
            cursor='hand2',
            command=browse_file
        ).pack(side='left', padx=(5, 0))

        # 预设颜色
        color_frame = tk.Frame(input_frame, bg=COLORS['bg_secondary'])
        color_frame.pack(fill='x', pady=(0, 10))

        tk.Label(
            color_frame,
            text='预设颜色:',
            font=('Microsoft YaHei', 9),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary'],
            width=14,
            anchor='w'
        ).pack(side='left')

        preset_colors = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#8B5CF6', '#EC4899', '#14B8A6']
        color_btn_frame = tk.Frame(color_frame, bg=COLORS['bg_secondary'])
        color_btn_frame.pack(side='left')

        def set_color(c):
            entries['color_entry'].delete(0, tk.END)
            entries['color_entry'].insert(0, c)

        for c in preset_colors:
            btn = tk.Button(
                color_btn_frame,
                bg=c,
                width=3,
                relief='flat',
                cursor='hand2',
                command=lambda color=c: set_color(color)
            )
            btn.pack(side='left', padx=2)

        # 按钮行
        btn_row = tk.Frame(dialog, bg=COLORS['bg_secondary'])
        btn_row.pack(pady=20)

        def do_add():
            name = entries['name_entry'].get().strip()
            path = entries['path_entry'].get().strip()
            icon = entries['icon_entry'].get().strip() or '📦'
            color = entries['color_entry'].get().strip() or '#6366F1'

            if not name:
                messagebox.showwarning('输入不完整', '请输入软件名称')
                return
            if not path:
                messagebox.showwarning('输入不完整', '请输入可执行文件路径')
                return

            import ntpath
            exe_name = ntpath.basename(path)

            new_software = {
                'name': name,
                'path': path,
                'exe': exe_name,
                'icon': icon,
                'color': color
            }

            # 检查是否已存在
            for s in self.launcher_software:
                if s.get('name') == name or s.get('path') == path:
                    messagebox.showwarning('已存在', f'"{name}" 已在列表中')
                    return

            self.launcher_software.append(new_software)
            save_software_list(self.launcher_software)
            self.refresh_launcher_cards()
            self.log(f'已添加软件: {name}')
            dialog.destroy()

        tk.Button(
            btn_row,
            text='取消',
            font=('Microsoft YaHei', 10),
            bg=COLORS['bg_card'],
            fg=COLORS['text_secondary'],
            relief='solid',
            padx=25,
            pady=6,
            cursor='hand2',
            command=dialog.destroy
        ).pack(side='left', padx=10)

        tk.Button(
            btn_row,
            text='添加',
            font=('Microsoft YaHei', 10),
            bg='#6366F1',
            fg='white',
            relief='flat',
            padx=25,
            pady=6,
            cursor='hand2',
            command=do_add
        ).pack(side='left')


def main():
    if not is_admin():
        run_as_admin()
        return

    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == '__main__':
    main()
