#!/bin/bash

# Comprehensive verification script for dbxclean

echo "🔍 dbxclean Verification Script"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# Function to print colored output
print_success() { echo "✅ $1"; }
print_error() { echo "❌ $1"; ((ERRORS++)); }
print_warning() { echo "⚠️  $1"; ((WARNINGS++)); }
print_info() { echo "ℹ️  $1"; }

# Check directory structure
echo "📁 Checking directory structure..."
[ -d "backend" ] && print_success "backend/ directory exists" || print_error "backend/ directory missing"
[ -d "frontend" ] && print_success "frontend/ directory exists" || print_error "frontend/ directory missing"
[ -d "backend/app" ] && print_success "backend/app/ directory exists" || print_error "backend/app/ directory missing"
[ -d "frontend/src" ] && print_success "frontend/src/ directory exists" || print_error "frontend/src/ directory missing"
echo ""

# Check key files
echo "📄 Checking key files..."
[ -f "README.md" ] && print_success "README.md exists" || print_warning "README.md missing"
[ -f "SETUP.md" ] && print_success "SETUP.md exists" || print_warning "SETUP.md missing"
[ -f ".gitignore" ] && print_success ".gitignore exists" || print_warning ".gitignore missing"
[ -f "backend/requirements.txt" ] && print_success "requirements.txt exists" || print_error "requirements.txt missing"
[ -f "backend/.env.example" ] && print_success ".env.example exists" || print_warning ".env.example missing"
[ -f "frontend/package.json" ] && print_success "package.json exists" || print_error "package.json missing"
echo ""

# Check Python
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"

    # Check version is 3.9+
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        print_success "Python version is 3.9+"
    else
        print_error "Python 3.9+ required, found $PYTHON_VERSION"
    fi
else
    print_error "Python 3 not found"
fi
echo ""

# Check virtual environment
echo "📦 Checking Python virtual environment..."
if [ -d "backend/venv" ]; then
    print_success "Virtual environment exists"

    # Check if activated packages are installed
    if [ -f "backend/venv/bin/python" ] || [ -f "backend/venv/Scripts/python.exe" ]; then
        print_success "Virtual environment is valid"
    else
        print_warning "Virtual environment might be corrupted"
    fi
else
    print_warning "Virtual environment not found (run: cd backend && python3 -m venv venv)"
fi
echo ""

# Check .env file
echo "⚙️  Checking configuration..."
if [ -f "backend/.env" ]; then
    print_success ".env file exists"

    # Check if DROPBOX_ACCESS_TOKEN is set
    if grep -q "DROPBOX_ACCESS_TOKEN=sl\." "backend/.env" 2>/dev/null; then
        print_success "DROPBOX_ACCESS_TOKEN appears to be configured"
    else
        print_warning "DROPBOX_ACCESS_TOKEN might not be configured"
    fi
else
    print_warning ".env file not found (copy from .env.example)"
fi
echo ""

# Check Node.js
echo "📦 Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"

    # Check version
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        print_success "Node.js version is 18+"
    else
        print_warning "Node.js 18+ recommended, found $NODE_VERSION"
    fi
else
    print_warning "Node.js not found (needed for frontend)"
fi
echo ""

# Check npm
echo "📦 Checking npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_warning "npm not found (needed for frontend)"
fi
echo ""

# Check node_modules
echo "📚 Checking dependencies..."
if [ -d "frontend/node_modules" ]; then
    print_success "Frontend node_modules installed"
else
    print_warning "Frontend dependencies not installed (run: cd frontend && npm install)"
fi
echo ""

# Check backend Python files
echo "🐍 Checking backend files..."
BACKEND_FILES=(
    "backend/app/__init__.py"
    "backend/app/main.py"
    "backend/app/config.py"
    "backend/app/database.py"
    "backend/app/dropbox_client.py"
    "backend/app/models.py"
    "backend/app/logging_config.py"
    "backend/app/validators.py"
)

for file in "${BACKEND_FILES[@]}"; do
    [ -f "$file" ] && print_success "$(basename $file)" || print_error "$file missing"
done
echo ""

# Check frontend files
echo "⚛️  Checking frontend files..."
FRONTEND_FILES=(
    "frontend/src/App.jsx"
    "frontend/src/main.jsx"
    "frontend/src/api.js"
    "frontend/src/pages/Dashboard.jsx"
    "frontend/src/pages/Duplicates.jsx"
    "frontend/src/pages/Similar.jsx"
    "frontend/src/pages/Files.jsx"
    "frontend/src/pages/Settings.jsx"
    "frontend/src/pages/NotFound.jsx"
)

for file in "${FRONTEND_FILES[@]}"; do
    [ -f "$file" ] && print_success "$(basename $file)" || print_error "$file missing"
done
echo ""

# Check ports
echo "🔌 Checking ports..."
if command -v lsof &> /dev/null; then
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8000 is in use (backend might be running)"
    else
        print_info "Port 8000 is available"
    fi

    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 3000 is in use (frontend might be running)"
    else
        print_info "Port 3000 is available"
    fi
else
    print_info "lsof not available, skipping port check"
fi
echo ""

# Summary
echo "======================================"
echo "📊 Verification Summary"
echo "======================================"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_success "All checks passed! ✨"
    echo ""
    echo "Ready to run! Start the application with:"
    echo "  ./start.sh"
    echo ""
    echo "Or manually:"
    echo "  Terminal 1: cd backend && source venv/bin/activate && python -m app.main"
    echo "  Terminal 2: cd frontend && npm run dev"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) found"
    echo ""
    echo "The application should work, but review warnings above."
    exit 0
else
    echo "❌ $ERRORS error(s) and $WARNINGS warning(s) found"
    echo ""
    echo "Please fix the errors above before running."
    exit 1
fi
