@echo off
chcp 65001 >nul
cd /d %~dp0
echo ==========================================================
echo  专业师生业绩管理系统 - 生产模式启动（waitress WSGI）
echo  启动前请确认已配置 .env（SECRET_KEY / JWT_SECRET_KEY）
echo  健康检查: http://127.0.0.1:5000/api/health
echo ==========================================================
echo.
set APP_ENV=production
"%~dp0..\.venv\Scripts\python.exe" app.py
echo.
echo 服务已退出，请检查上方日志。
pause