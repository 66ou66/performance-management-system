@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  专业师生业绩管理系统 - 前端开发服务
echo  访问地址: http://127.0.0.1:5173/
echo  关闭本窗口即可停止服务
echo ============================================
echo.
call npm run dev -- --host 127.0.0.1
echo.
echo 前端服务已退出。
pause