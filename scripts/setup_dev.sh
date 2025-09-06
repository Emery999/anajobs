#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up AnaJobs development environment..."

# Check Python version
echo "📍 Checking Python version..."
python3 -c "
import sys
version = f'{sys.version_info.major}.{sys.version_info.minor}'
print(f'Python version: {version}')
if sys.version_info < (3, 8):
    print('❌ Python 3.8+ required. Current version: ' + version)
    sys.exit(1)
else:
    print('✅ Python version check passed')
"

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "🔧 Installing dependencies..."
pip install -r requirements.txt

# Install in development mode
echo "🔧 Installing package in development mode..."
pip install -e ".[dev]"

# Create necessary directories
echo "🔧 Creating necessary directories..."
mkdir -p logs
mkdir -p config

# Create default configuration
echo "🔧 Creating default configuration..."
python -c "from src.anajobs.config import create_default_config; create_default_config()"

# Set up pre-commit hooks (if available)
if command -v pre-commit &> /dev/null; then
    echo "🔧 Setting up pre-commit hooks..."
    pre-commit install
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  pre-commit not found, skipping hooks setup"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Start MongoDB: sudo systemctl start mongod (or brew services start mongodb-community)"
echo "3. Run setup: python -m anajobs.cli setup"
echo "4. Run tests: pytest"
echo ""
echo "Useful commands:"
echo "  - anajobs setup                    # Setup database"
echo "  - anajobs test                     # Test database"
echo "  - anajobs search 'term'           # Search organizations"
echo "  - anajobs stats                    # Show statistics"
echo "  - pytest                          # Run tests"
echo "  - black src/ tests/               # Format code"
echo "  - flake8 src/ tests/              # Check code style"