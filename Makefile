.PHONY: help install verify start stop clean test backend frontend

help:
	@echo "dbxclean - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "  make install    - Install all dependencies"
	@echo "  make verify     - Verify installation"
	@echo "  make start      - Start both backend and frontend"
	@echo "  make stop       - Stop all services"
	@echo "  make backend    - Start backend only"
	@echo "  make frontend   - Start frontend only"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make test       - Run tests (if available)"
	@echo ""

install:
	@echo "🚀 Installing dbxclean..."
	@chmod +x install.sh
	@./install.sh

verify:
	@echo "🔍 Verifying installation..."
	@chmod +x verify.sh
	@./verify.sh

start:
	@echo "🚀 Starting dbxclean..."
	@chmod +x start.sh
	@./start.sh

stop:
	@echo "🛑 Stopping services..."
	@chmod +x stop.sh
	@./stop.sh

backend:
	@echo "🐍 Starting backend..."
	@cd backend && source venv/bin/activate && python -m app.main

frontend:
	@echo "⚛️  Starting frontend..."
	@cd frontend && npm run dev

clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf backend/__pycache__
	@rm -rf backend/app/__pycache__
	@rm -rf backend/app/*/__pycache__
	@rm -rf backend/*.db
	@rm -rf backend/logs
	@rm -rf frontend/dist
	@rm -rf frontend/.vite
	@rm -f backend.log frontend.log
	@rm -f .pids
	@echo "✅ Clean complete!"

test:
	@echo "🧪 Running tests..."
	@echo "⚠️  Tests not yet implemented"
