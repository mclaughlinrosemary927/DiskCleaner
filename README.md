# DiskCleaner

Windows desktop utility for reviewing disk usage, scanning safe-to-clean files,
managing common applications, and exposing Quark Cloud Drive in File Explorer.

## Included Features

- Disk overview with safe-cleanup scan results and a dedicated results scrollbar.
- Cleanup for temporary files, browser caches, update leftovers, logs, and recycle-bin data.
- Process and startup-app management views.
- Application launcher cards with local application icons.
- Quark Cloud Drive mounted as a fixed drive in File Explorer after Windows sign-in.
- Light workbench-style desktop UI and a packaged standalone executable.

## Run

Open the packaged application:

```text
dist\DiskCleaner.exe
```

For source development, run:

```powershell
python disk_cleaner_gui_v8.py
```

## Build

After changing `disk_cleaner_gui_v8.py`, rebuild the executable:

```powershell
scripts\build_exe.bat
```

The generated application is written to `dist\DiskCleaner.exe`.

## Quark Cloud Drive

The Quark device-drive launcher is in:

```text
scripts\mount_quark_device_drive.ps1
```

It uses a local WebDAV bridge and rclone/WinFsp to present Quark Cloud Drive
as a fixed drive in File Explorer. See
[`scripts/QuarkDeviceDrive-README.md`](scripts/QuarkDeviceDrive-README.md)
for authorization and recovery instructions.

## GitHub Sync Scripts

The helper scripts are in `scripts/`:

- `upload_to_github.bat`
- `download_from_github.bat`
- `github_sync.py`

Local authorization files, runtime logs, caches, and user data are excluded
from Git tracking.

## Project Layout

```text
disk_cleaner_gui_v8.py    Main desktop application
assets/                   Application and launcher icons
scripts/                  Build, sync, and Quark mounting utilities
dist/                     Packaged executable
CHANGELOG.md              Release and cleanup log
```
