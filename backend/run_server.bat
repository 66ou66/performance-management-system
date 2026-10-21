@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  专业师生业绩管理系统 - 后端服务
echo  接口地址: http://127.0.0.1:5000/api/health
echo  关闭本窗口即可停止服务
echo ============================================
echo.
"%~dp0..\.venv\Scripts\python.exe" app.py
echo.
echo 后端服务已退出。
pause