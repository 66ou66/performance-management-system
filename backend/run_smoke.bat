@echo off
chcp 65001 >nul
cd /d %~dp0
echo 正在执行接口冒烟测试...
"%~dp0..\.venv\Scripts\python.exe" -u smoke_test.py > smoke.log 2>&1
echo SMOKE_EXIT=%ERRORLEVEL% >> smoke.log
echo.
echo 测试完成，结果见 backend\smoke.log（末尾 SMOKE_TEST_DONE 表示全部通过）。
pause