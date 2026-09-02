@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
REM Build TBCheck.exe, TBCheckRename.exe, and TBCheckCustom.exe with the project venv.
echo ============================================
echo Building TBCheck.exe, TBCheckRename.exe, and TBCheckCustom.exe
echo ============================================
echo.

set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY=%~dp0.venv\Scripts\python.exe"
    echo Using project venv
) else (
    echo Using Python from PATH
)
echo.

echo Installing/updating build dependencies...
"%PY%" -m pip install -q -e ".[build]"
if errorlevel 1 (
    echo.
    echo ERROR: Could not install dependencies.
    pause
    exit /b 1
)
echo.

if exist "build" (
    echo Cleaning build directory...
    rmdir /s /q build
)
if exist "TBCheck.spec" del TBCheck.spec
if exist "TBCheckRename.spec" del TBCheckRename.spec
if exist "TBCheckCustom.spec" del TBCheckCustom.spec

"%PY%" scripts\build_exe.py
if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    pause
    exit /b 1
)

if exist "TBCheck.spec" del TBCheck.spec
if exist "TBCheckRename.spec" del TBCheckRename.spec
if exist "TBCheckCustom.spec" del TBCheckCustom.spec

echo.
echo ============================================
echo Build complete
echo ============================================
echo.
echo Executables:
echo   dist\TBCheck.exe        QA report + optional mismatch filename fix
echo   dist\TBCheckRename.exe  QA report + auto-rename to doc-ref_title_revision
echo   dist\TBCheckCustom.exe  QA report with --disable / --checks to toggle QA rules
echo.
echo Copy an exe into a folder of drawing PDFs and double-click.
echo Optional: copy a config\ folder next to the exe to override layouts.
echo ============================================
pause
