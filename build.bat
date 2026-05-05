@echo off
chcp 65001
setlocal enabledelayedexpansion

:: --- 1. 基础路径配置 ---
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "VS_DEV_CMD=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\Tools\VsDevCmd.bat"
set "CERT_PATH=%PROJECT_DIR%\mycert.pfx"
set "CERT_PWD=123456"
set "ICON_FILE=%PROJECT_DIR%\tray_icon.ico"
set "TARGET_EXE=%PROJECT_DIR%\out\ChronoGlass.exe"

cd /d "%PROJECT_DIR%"

echo ======================================================
echo           ChronoGlass 环境体检 (作者: HuanQingYi)
echo ======================================================

:: --- 2. 自动化检测逻辑 ---

set "HEALTH_CHECK=PASS"

echo [检测] 虚拟环境...
if not exist "%VENV_PYTHON%" (
    echo    -^> [错误] 找不到 .venv 文件夹，请确认环境已创建。
    set "HEALTH_CHECK=FAIL"
) else ( echo    -^> OK )

echo [检测] 数字证书...
if not exist "%CERT_PATH%" (
    echo    -^> [错误] 目录下缺少 mycert.pfx 证书文件。
    set "HEALTH_CHECK=FAIL"
) else ( echo    -^> OK )

echo [检测] 图标资源...
if not exist "%ICON_FILE%" (
    echo    -^> [错误] 目录下缺少 tray_icon.ico 文件。
    set "HEALTH_CHECK=FAIL"
) else ( echo    -^> OK )

echo [检测] VS2019 工具链...
if not exist "%VS_DEV_CMD%" (
    echo    -^> [错误] 找不到 VS2019 编译环境，请检查路径。
    set "HEALTH_CHECK=FAIL"
) else ( echo    -^> OK )

:: --- 3. 环境判定与清理 ---

if "%HEALTH_CHECK%"=="FAIL" (
    echo.
    echo [中止] 环境体检未通过，请修复上述问题后再试。
    pause
    exit /b
)

echo.
echo [准备] 环境检查无误，正在清理旧的 out 目录...
if exist "out" (
    set "OUT_JSON_BACKUP=%PROJECT_DIR%\.out_json_backup"
    if exist "!OUT_JSON_BACKUP!" rd /s /q "!OUT_JSON_BACKUP!"
    md "!OUT_JSON_BACKUP!" >nul
    move /y "out\*.json" "!OUT_JSON_BACKUP!" >nul 2>nul
    pushd "out"
    for /d %%D in (*) do rd /s /q "%%D" >nul 2>nul
    del /f /q * >nul 2>nul
    popd
    move /y "!OUT_JSON_BACKUP!\*.json" "out" >nul 2>nul
    rd /s /q "!OUT_JSON_BACKUP!" >nul 2>nul
    echo    -^> 已清理旧内容，并保留 out 根目录下的 .json 文件。
) else (
    echo    -^> 目录已是洁净状态。
)
echo.

:: --- 4. 执行打包 ---

echo [1/2] 正在执行 Nuitka 高级打包...
"%VENV_PYTHON%" -m nuitka --standalone --onefile ^
--lto=yes ^
--jobs=4 ^
--plugin-enable=upx ^
--onefile-no-compression ^
--windows-console-mode=disable ^
--enable-plugin=pyqt6 ^
--include-qt-plugins=imageformats ^
--windows-icon-from-ico=tray_icon.ico ^
--include-data-files="tray_icon.png=tray_icon.png" ^
--windows-company-name="HuanQingYi" ^
--product-name="ChronoGlass" ^
--windows-file-description="ChronoGlass - 极简几何计时器" ^
--copyright="Copyright (C) 2026 HuanQingYi. All rights reserved." ^
--file-version=1.2.0.0 ^
--windows-product-version=1.2.0.0 ^
--output-dir=out ^
ChronoGlass.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] Nuitka 编译过程中断，请检查上方 Python 报错。
    pause
    exit /b
)

:: --- 5. 执行签名 ---

echo.
echo [2/2] 正在盖章签名 (VS2019 Dev Context)...
call "%VS_DEV_CMD%"
signtool sign /f "%CERT_PATH%" /p %CERT_PWD% /fd SHA256 /t http://timestamp.digicert.com /v "%TARGET_EXE%"

echo.
echo ======================================================
echo 构建成功！你的 ChronoGlass 已准备就绪。
echo By_HuanQingYi
echo ======================================================
pause
