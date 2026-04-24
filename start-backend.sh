#!/bin/bash

echo "🔧 Starting Flask Backend Server..."
echo "📂 Working directory: $(pwd)"

# Kill any existing Flask processes on port 5001
echo "🚫 Killing any existing processes on port 5001..."
lsof -ti :5001 | xargs kill -9 2>/dev/null || true

# Change to backend directory if it exists, otherwise stay in current directory
if [ -d "backend" ]; then
    cd backend
    echo "📁 Changed to backend directory"
fi

# Start the Flask server
echo "🚀 Starting Flask server on port 5001..."
python app.py