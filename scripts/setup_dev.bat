@echo off
REM Development environment setup script for Windows

echo 🚀 Setting up AnaJobs development environment...

REM Check Python version
echo 📍 Checking Python version...
python -c "import sys; version = f'{sys.version_info.major}.{sys.version_info.minor}'; print(f'Python version: {version}'); exit(0 if sys.version_info >= (3, 8) else 1)"
if errorlevel 1 (
    echo ❌ Python 3.8+ required
    exit /b 1
)

echo ✅ Python version check passed

REM Create virtual environment
echo 🔧 Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Upgrade pip
echo 🔧 Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 🔧 Installing dependencies...
pip install -r requirements.txt

REM Install in development mode
echo 🔧 Installing package in development mode...
pip install -e ".[dev]"

REM Create necessary directories
echo 🔧 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "config" mkdir config

REM Create default configuration
echo 🔧 Creating default configuration...
python -c "from src.anajobs.config import create_default_config; create_default_config()"

echo.
echo 🎉 Development environment setup complete!
echo.
echo Next steps:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Start MongoDB (if using local instance)
echo 3. Run setup: python -m anajobs.cli setup
echo 4. Run tests: pytest
echo.
echo Useful commands:
echo   - anajobs setup                    # Setup database
echo   - anajobs test                     # Test database
echo   - anajobs search "term"            # Search organizations
echo   - anajobs stats                    # Show statistics
echo   - pytest                          # Run tests
echo   - black src/ tests/               # Format code
echo   - flake8 src/ tests/              # Check code style

pause