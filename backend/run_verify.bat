@echo off
chcp 65001 >nul
cd /d %~dp0
"%~dp0..\.venv\Scripts\python.exe" -u verify_flows.py
echo.
echo 校验结束，按任意键关闭窗口。
pause >nul