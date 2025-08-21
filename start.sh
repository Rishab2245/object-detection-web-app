#!/bin/bash

# WebRTC VLM Object Detection - Start Script
# Usage: ./start.sh [--mode=wasm|server] [--ngrok] [--build]

set -e

# Default values
MODE="wasm"
USE_NGROK=false
BUILD=false
HELP=false

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --mode=*)
            MODE="${arg#*=}"
            shift
            ;;
        --ngrok)
            USE_NGROK=true
            shift
            ;;
        --build)
            BUILD=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown argument: $arg"
            HELP=true
            ;;
    esac
done

# Show help
if [ "$HELP" = true ]; then
    echo "WebRTC VLM Object Detection - Start Script"
    echo ""
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --mode=MODE     Set detection mode (wasm|server) [default: wasm]"
    echo "  --ngrok         Use ngrok for external access"
    echo "  --build         Force rebuild Docker images"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh                    # Start with WASM mode"
    echo "  ./start.sh --mode=server      # Start with server-side inference"
    echo "  ./start.sh --ngrok            # Start with ngrok for phone access"
    echo "  ./start.sh --build            # Force rebuild and start"
    echo ""
    exit 0
fi

# Validate mode
if [ "$MODE" != "wasm" ] && [ "$MODE" != "server" ]; then
    echo "Error: Invalid mode '$MODE'. Must be 'wasm' or 'server'."
    exit 1
fi

echo "🚀 Starting WebRTC VLM Object Detection"
echo "📋 Mode: $MODE"
echo "🌐 Ngrok: $USE_NGROK"
echo "🔨 Build: $BUILD"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "Please install Docker and try again"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    echo "Please install Docker Compose and try again"
    exit 1
fi

# Build flag for docker-compose
BUILD_FLAG=""
if [ "$BUILD" = true ]; then
    BUILD_FLAG="--build"
    echo "🔨 Building Docker images..."
fi

# Set environment variables
export DETECTION_MODE=$MODE

# Start services
echo "🐳 Starting Docker services..."
if [ "$BUILD" = true ]; then
    docker-compose up --build -d
else
    docker-compose up -d
fi

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Failed to start services"
    echo "Checking logs..."
    docker-compose logs
    exit 1
fi

echo "✅ Services started successfully!"
echo ""
echo "📱 Application URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:5000"
echo ""

# Setup ngrok if requested
if [ "$USE_NGROK" = true ]; then
    if command -v ngrok &> /dev/null; then
        echo "🌐 Starting ngrok tunnel..."
        ngrok http 3000 --log=stdout > ngrok.log 2>&1 &
        NGROK_PID=$!
        sleep 3
        
        # Extract ngrok URL
        if command -v curl &> /dev/null; then
            NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok\.io')
            if [ -n "$NGROK_URL" ]; then
                echo "📱 Phone URL: $NGROK_URL"
                echo "📱 Scan the QR code in the app or visit the URL above on your phone"
            else
                echo "⚠️  Could not retrieve ngrok URL. Check ngrok.log for details."
            fi
        fi
        
        # Save ngrok PID for cleanup
        echo $NGROK_PID > ngrok.pid
    else
        echo "⚠️  ngrok not found. Install ngrok for external access:"
        echo "   https://ngrok.com/download"
        echo ""
        echo "📱 For phone access, ensure your phone and computer are on the same network"
        echo "📱 Use your computer's IP address: http://[YOUR_IP]:3000"
    fi
fi

echo ""
echo "🎯 Detection Mode: $MODE"
if [ "$MODE" = "wasm" ]; then
    echo "   • Object detection runs in the browser (WASM)"
    echo "   • Lower server resource usage"
    echo "   • Suitable for modest hardware"
else
    echo "   • Object detection runs on the server"
    echo "   • Higher accuracy and performance"
    echo "   • Requires more server resources"
fi

echo ""
echo "🛑 To stop the application:"
echo "   docker-compose down"
if [ "$USE_NGROK" = true ]; then
    echo "   kill \$(cat ngrok.pid) && rm ngrok.pid  # Stop ngrok"
fi

echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🎉 Application is ready! Open http://localhost:3000 in your browser."

