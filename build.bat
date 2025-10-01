@echo off
echo ========================================
echo RTF2PDF Build Script
echo ========================================

REM Check if py is available
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: py is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing/updating dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Building GUI executable...
echo ========================================
pyinstaller --clean build_gui.spec
if errorlevel 1 (
    echo ERROR: Failed to build GUI executable
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo Executable: dist\RTF2PDF_GUI.exe
echo.
echo Note: The executable is standalone and includes all dependencies.
echo.
pause 