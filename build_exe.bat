@echo off
REM Build TBCheck.exe — drop it into a folder of PDFs and double-click.
echo ============================================
echo Building TBCheck.exe
echo ============================================
echo.

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    echo.
)

if exist "build" (
    echo Cleaning build directory...
    rmdir /s /q build
)
if exist "TBCheck.spec" (
    del TBCheck.spec
)

python scripts\build_exe.py
if errorlevel 1 (
    echo.
    echo ERROR: Build failed for TBCheck.exe
    pause
    exit /b 1
)

if exist "TBCheck.spec" (
    del TBCheck.spec
)

echo.
echo ============================================
echo Build complete
echo ============================================
echo.
echo Executable: dist\TBCheck.exe
echo.
echo Copy TBCheck.exe into a folder of drawing PDFs and double-click.
echo Optional: copy a config\ folder next to the exe to override layouts.
echo ============================================
pause
