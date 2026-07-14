# 夸克网盘设备驱动器

夸克网盘会显示为资源管理器“此电脑”的“设备和驱动器”中的 `X:`，卷标为“夸克网盘”。

## 当前配置

- 计划任务：`DiskCleaner-QuarkDeviceDrive`
- 触发条件：`Administrator` 登录 Windows 后自动运行
- 挂载方式：本机 WebDAV 桥接 + rclone + WinFsp
- 网络范围：桥接服务仅监听 `127.0.0.1:5245`，不向局域网开放
- 挂载模式：只读。浏览、打开、复制和下载不会改动云端文件；删除、重命名、上传等写入操作会被拒绝。

## 手动恢复

如果 `X:` 没有出现，以 Administrator 身份打开 PowerShell 后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Program Files\ChatGPT\Projects\DiskCleaner\scripts\mount_quark_device_drive.ps1"
```

## 授权过期

夸克登录凭据过期时，重新运行：

```powershell
python scripts\quark_authorize.py
```

然后用夸克 App 扫描生成的 `quark_authorize_qr.png`。确认后再次运行上面的手动恢复命令，或注销后重新登录。

不要使用旧版 AList 2.x 的夸克配置：该版本不含夸克存储驱动，无法完成挂载。
