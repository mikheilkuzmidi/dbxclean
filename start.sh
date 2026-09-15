#!/bin/bash

# dbxclean - Quick Start Script

echo "🚀 Starting dbxclean..."
echo ""

# Check if venv exists
if [ ! -d "backend/venv" ]; then
    echo "⚠️  Python virtual environment not found. Creating..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  Node modules not found. Installing..."
    cd frontend
    npm install
    cd ..
fi

echo "✅ All dependencies ready!"
echo ""
echo "Starting services..."
echo ""

# Start backend in background
echo "📡 Starting backend on http://localhost:8000..."
cd backend
source venv/bin/activate
python -m app.main > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend in background
echo "🎨 Starting frontend on http://localhost:3000..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ dbxclean is running!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔧 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "To stop the services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop (may need to run kill command after)"
echo ""

# Save PIDs to file for easy cleanup
echo "$BACKEND_PID" > .pids
echo "$FRONTEND_PID" >> .pids

# Wait for user interrupt
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .pids; echo 'Stopped.'; exit 0" INT

wait
