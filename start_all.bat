@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0start_app.bat"
echo.
echo 使用提示：保持「业绩管理系统-后端」「业绩管理系统-前端」两个窗口开启，关闭它们即停止服务。
pause