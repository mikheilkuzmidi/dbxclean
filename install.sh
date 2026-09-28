#!/bin/bash

# Installation script for dbxclean

echo "🚀 dbxclean Installation"
echo "==============================="
echo ""

set -e  # Exit on error

# Check Python
echo "📝 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION found"

# Check Node
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found. Frontend will not be available."
    echo "   Install from: https://nodejs.org/"
    NODE_AVAILABLE=false
else
    NODE_VERSION=$(node --version)
    echo "✅ Node.js $NODE_VERSION found"
    NODE_AVAILABLE=true
fi

echo ""

# Backend setup
echo "🐍 Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ Failed to find venv activation script"
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Set LOCAL_ROOT in backend/.env to the folder you want to scan. Dropbox mode is optional."
fi

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

# Check requirements
echo "Verifying backend setup..."
python scripts/check_requirements.py || echo "Configure backend/.env before starting the app."

cd ..

echo "✅ Backend setup complete!"
echo ""

# Frontend setup
if [ "$NODE_AVAILABLE" = true ]; then
    echo "⚛️  Setting up frontend..."
    cd frontend

    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies (this may take a few minutes)..."
        npm ci
    else
        echo "Node modules already installed"
    fi

    cd ..
    echo "✅ Frontend setup complete!"
else
    echo "⚠️  Skipping frontend setup (Node.js not available)"
fi

echo ""
echo "======================================"
echo "✅ Installation complete!"
echo "======================================"
echo ""

echo "Set LOCAL_ROOT in backend/.env to an existing directory, then run ./start.sh."
echo "Dropbox mode needs a Dropbox access token only when you choose it."

echo ""
echo "For more information, see SETUP.md"
echo ""
