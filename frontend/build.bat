@echo off
cd /d %~dp0
call npm run build > build.log 2>&1
echo BUILD_EXIT=%ERRORLEVEL% >> build.log