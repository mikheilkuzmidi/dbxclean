#!/bin/bash

# Installation script for dbxclean

echo "🚀 dbxclean Installation"
echo "==============================="
echo ""

set -e  # Exit on error

# Check Python
echo "📝 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9 or higher."
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
    echo "⚠️  Please edit backend/.env and add your DROPBOX_ACCESS_TOKEN"
fi

# Initialize database
echo "Initializing database..."
python scripts/init_db.py

# Check requirements
echo "Verifying backend setup..."
python scripts/check_requirements.py

cd ..

echo "✅ Backend setup complete!"
echo ""

# Frontend setup
if [ "$NODE_AVAILABLE" = true ]; then
    echo "⚛️  Setting up frontend..."
    cd frontend

    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies (this may take a few minutes)..."
        npm install
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

if [ ! -f "backend/.env" ] || ! grep -q "DROPBOX_ACCESS_TOKEN=sl\." "backend/.env" 2>/dev/null; then
    echo "⚠️  Next steps:"
    echo "1. Get your Dropbox access token:"
    echo "   - Visit: https://www.dropbox.com/developers/apps"
    echo "   - Create app with Full Dropbox access"
    echo "   - Enable permissions: files.metadata.read, files.content.read, files.content.write"
    echo "   - Generate access token"
    echo ""
    echo "2. Edit backend/.env and add your token:"
    echo "   DROPBOX_ACCESS_TOKEN=your_token_here"
    echo ""
    echo "3. Start the application:"
    echo "   ./start.sh"
else
    echo "🎉 Ready to run!"
    echo ""
    echo "Start the application with:"
    echo "  ./start.sh"
    echo ""
    echo "Or manually:"
    echo "  Terminal 1: cd backend && source venv/bin/activate && python -m app.main"
    echo "  Terminal 2: cd frontend && npm run dev"
fi

echo ""
echo "For more information, see SETUP.md"
echo ""
