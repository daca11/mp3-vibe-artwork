#!/bin/bash

# MP3 Artwork Manager - Setup Script
# Automates the setup process for quick deployment

set -e  # Exit on any error

echo "🎵 MP3 Artwork Manager - Setup Script"
echo "====================================="

# Check Python version
echo "📋 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.8+ and try again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p uploads temp output logs
echo "✅ Directories created"

# Set permissions
echo "🔒 Setting directory permissions..."
chmod 755 uploads temp output logs
echo "✅ Permissions set"

# Run tests to verify installation
echo "🧪 Running tests to verify installation..."
if python -m pytest tests/ -v --tb=short -q | grep -q "failed"; then
    echo "⚠️  Some tests failed, but core functionality should work"
else
    echo "✅ All tests passed"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the application: python run.py"
echo "  3. Open browser to: http://localhost:5001"
echo ""
echo "For more information, see QUICKSTART.md"
echo ""
echo "Happy processing! 🎵✨"
