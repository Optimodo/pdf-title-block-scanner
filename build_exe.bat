@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
REM Build the versioned QA-TB executables with the project venv.
echo ============================================
echo Building QA-TB-Checker, Custom-Checker, and File-Renamer
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
del /q QA-TB-*.spec TBCheck.spec TBCheckRename.spec TBCheckCustom.spec 2>nul

"%PY%" scripts\build_exe.py
if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    pause
    exit /b 1
)

del /q QA-TB-*.spec TBCheck.spec TBCheckRename.spec TBCheckCustom.spec 2>nul

echo.
echo ============================================
echo Build complete
echo ============================================
echo.
echo Executables (version is in the file name so you can see if a copy is older):
echo   dist\QA-TB-Checker-v*.exe         QA report + optional mismatch filename fix
echo   dist\QA-TB-File-Renamer-v*.exe    QA report + auto-rename to doc-ref_title_revision
echo   dist\QA-TB-Custom-Checker-v*.exe  QA report with a menu to turn checks on or off
echo.
echo Copy an exe into a folder of drawing PDFs and double-click.
echo Optional: copy a config\ folder next to the exe to override layouts.
echo ============================================
pause
