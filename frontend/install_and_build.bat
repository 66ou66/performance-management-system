@echo off
chcp 65001 >nul
cd /d %~dp0
echo 正在清理并重新安装前端依赖（镜像：https://registry.npmmirror.com）...
if exist node_modules rmdir /s /q node_modules
if exist package-lock.json del /q package-lock.json
call npm install --registry=https://registry.npmmirror.com --no-audit --no-fund > npm-install.log 2>&1
echo NPM_EXIT=%ERRORLEVEL% >> npm-install.log
if exist node_modules\element-plus\es\index.mjs (echo ELEMENT_PLUS_OK >> npm-install.log) else (echo ELEMENT_PLUS_MISSING >> npm-install.log)
echo 正在构建生产版本...
call npm run build > build.log 2>&1
echo BUILD_EXIT=%ERRORLEVEL% >> build.log
echo.
echo 完成：npm-install.log 末尾 NPM_EXIT=0、ELEMENT_PLUS_OK 为正常；build.log 末尾 BUILD_EXIT=0 为正常。
pause