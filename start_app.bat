@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem 参数 -n：启动后不自动打开浏览器（用于自动化验证）
set "OPEN=1"
if /i "%~1"=="-n" set "OPEN=0"

echo ============================================
echo  专业师生业绩管理系统 - 一键启动
echo ============================================
echo.

echo [1/3] 检查后端服务 http://127.0.0.1:5000 ...
curl -s -m 2 -o nul http://127.0.0.1:5000/api/health
if not errorlevel 1 (
    echo       后端已在运行，跳过启动。
    goto backend_ready
)
echo       正在启动后端（新窗口）...
start "业绩管理系统-后端" /d "%~dp0backend" cmd /k "..\.venv\Scripts\python.exe app.py"
call :wait_url "http://127.0.0.1:5000/api/health" 40
if errorlevel 1 (
    echo       后端启动超时，请查看「业绩管理系统-后端」窗口中的错误信息。
    goto failed
)
:backend_ready

echo [2/3] 检查前端服务 http://127.0.0.1:5173 ...
curl -s -m 2 -o nul http://127.0.0.1:5173/
if not errorlevel 1 (
    echo       前端已在运行，跳过启动。
    goto frontend_ready
)
echo       正在启动前端（新窗口）...
start "业绩管理系统-前端" /d "%~dp0frontend" cmd /k "npm run dev -- --host 127.0.0.1"
call :wait_url "http://127.0.0.1:5173/" 90
if errorlevel 1 (
    echo       前端启动超时，请查看「业绩管理系统-前端」窗口中的 npm 输出。
    goto failed
)
:frontend_ready

if "%OPEN%"=="1" (
    echo [3/3] 打开系统页面 ...
    start "" "http://127.0.0.1:5173/"
) else (
    echo [3/3] 已跳过打开浏览器（-n 模式）。
)
echo.
echo 演示账号：管理员 admin / admin123    教师 teacher1 / 123456    学生 student1 / 123456
echo 关闭「业绩管理系统-后端」与「业绩管理系统-前端」两个窗口即可停止服务。
ping -n 4 127.0.0.1 >nul
exit /b 0

:failed
echo.
echo 启动失败，请按上方提示检查；详细日志见后端 / 前端窗口。
ping -n 8 127.0.0.1 >nul
exit /b 1

:wait_url
set "WAIT_URL=%~1"
set /a WAIT_LEFT=%~2
:wait_loop
curl -s -m 2 -o nul "%WAIT_URL%"
if not errorlevel 1 exit /b 0
set /a WAIT_LEFT-=1
if %WAIT_LEFT% leq 0 exit /b 1
ping -n 2 127.0.0.1 >nul
goto wait_loop