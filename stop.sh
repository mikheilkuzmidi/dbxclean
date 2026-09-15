#!/bin/bash

# Stop dbxclean services

echo "🛑 Stopping dbxclean..."

if [ -f ".pids" ]; then
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping process $pid..."
            kill $pid 2>/dev/null
        fi
    done < .pids
    rm -f .pids
    echo "✅ Services stopped"
else
    echo "⚠️  No PID file found. Services might not be running."
    echo "You can manually stop them with:"
    echo "  pkill -f 'python -m app.main'"
    echo "  pkill -f 'vite'"
fi
