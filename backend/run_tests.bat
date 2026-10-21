@echo off
chcp 65001 >nul
cd /d %~dp0
echo 正在运行 pytest 单元/接口测试（使用独立临时数据库，不影响 app.db）...
echo.
"%~dp0..\.venv\Scripts\python.exe" -X utf8 -m pytest tests -q
set TEST_EXIT=%ERRORLEVEL%
echo.
echo PYTEST_EXIT=%TEST_EXIT%
echo 测试结束，按任意键关闭窗口。
pause >nul