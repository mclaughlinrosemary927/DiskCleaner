@echo off
setlocal
title Build DiskCleaner EXE

set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

where python >nul 2>&1
if errorlevel 1 goto :missing_python

python -m PyInstaller --noconfirm --clean --noconsole --onefile --name DiskCleaner --icon "%PROJECT_ROOT%\app_icon.ico" --add-data "%PROJECT_ROOT%\app_icon.ico;." --add-data "%PROJECT_ROOT%\app_icon.png;." --add-data "%PROJECT_ROOT%\assets;assets" --distpath "dist" --workpath "build\pyinstaller" --specpath "build\pyinstaller" "%PROJECT_ROOT%\disk_cleaner_gui_v8.py"
if errorlevel 1 goto :build_failed

echo.
echo Build succeeded: dist\DiskCleaner.exe
goto :finish

:missing_python
echo.
echo Build failed: Python 3.12+ was not found.
goto :finish_error

:build_failed
echo.
echo Build failed. Review the PyInstaller output above.
goto :finish_error

:finish
popd
if not defined DISKCLEANER_NO_PAUSE pause
endlocal
exit /b 0

:finish_error
popd
if not defined DISKCLEANER_NO_PAUSE pause
endlocal
exit /b 1
