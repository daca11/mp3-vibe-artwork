@echo off
REM MP3 Artwork Manager - Setup Script for Windows
REM Automates the setup process for quick deployment

echo 🎵 MP3 Artwork Manager - Setup Script
echo =====================================

REM Check Python version
echo 📋 Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Create necessary directories
echo 📁 Creating application directories...
if not exist "uploads" mkdir uploads
if not exist "temp" mkdir temp
if not exist "output" mkdir output
if not exist "logs" mkdir logs
echo ✅ Directories created

REM Run basic test to verify installation
echo 🧪 Testing installation...
python -c "import flask, mutagen, PIL; print('✅ Core dependencies installed successfully')"

echo.
echo 🎉 Setup complete!
echo.
echo To start the application:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run the application: python run.py
echo   3. Open browser to: http://localhost:5001
echo.
echo For more information, see QUICKSTART.md
echo.
echo Happy processing! 🎵✨
pause
