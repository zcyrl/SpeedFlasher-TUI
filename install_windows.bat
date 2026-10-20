@echo off
setlocal enabledelayedexpansion
title SpeedFlasher TUI - Windows Setup
cd /d "%~dp0"

echo ========================================================================
echo       SpeedFlasher TUI (Antumbra Edition) - Windows Setup
echo       By Mehraann (patched UI by Softbrick)
echo ========================================================================
echo.

call "%~dp0setup.bat"
if %errorlevel% neq 0 (
    echo [!] Setup failed. Please ensure Python 3 is installed.
    pause
    exit /b 1
)

echo.
echo [*] Creating Desktop Shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'SpeedFlasher TUI.lnk')); $s.TargetPath = '%~dp0start.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'SpeedFlasher TUI by Mehraann (patched by Softbrick)'; $s.Save()" 2>nul
if %errorlevel% equ 0 (
    echo [✓] Shortcut 'SpeedFlasher TUI' created on your Desktop!
) else (
    echo [!] Could not create desktop shortcut automatically. You can run start.bat directly.
)

echo.
echo ========================================================================
echo [✓] Installation complete!
echo Double-click 'start.bat' or the Desktop shortcut to launch SpeedFlasher TUI.
echo ========================================================================
echo.
pause
