@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0assets\app.ico" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0tools\make_icon.py"
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\create_shortcut.ps1"
echo.
echo 桌面快捷方式已创建或更新；以后移动项目文件夹后，重新运行本文件即可修复路径。
pause