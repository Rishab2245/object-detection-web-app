# Real-Time WebRTC VLM Object Detection

A web-based application that performs real-time multi-object detection on live video streams from phones via WebRTC, with Vision Language Model (VLM) integration and overlay functionality.

## 🎯 Features

- **Real-time Object Detection**: Live video processing with bounding box overlays
- **WebRTC Streaming**: Direct phone-to-browser video streaming
- **Dual Processing Modes**: 
  - **WASM Mode**: On-device inference for low-resource environments
  - **Server Mode**: Server-side inference for higher accuracy
- **Performance Metrics**: Real-time latency and FPS monitoring
- **Cross-Platform**: Works on desktop and mobile browsers
- **Docker Support**: One-command deployment with Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Modern web browser with WebRTC support
- Camera-enabled device (phone/laptop)

### One-Command Start

```bash
git clone <repository>
cd webrtc-vlm-detection
./start.sh
```

Open http://localhost:3000 in your browser and click "Start Detection".

### Mode Selection

```bash
# WASM mode (default) - runs on modest hardware
./start.sh --mode=wasm

# Server mode - higher accuracy, more resources
./start.sh --mode=server

# With ngrok for phone access
./start.sh --ngrok
```

## 📱 Phone Connection

### Option 1: QR Code (Recommended)
1. Start the application with `./start.sh --ngrok`
2. Scan the QR code displayed in the web interface with your phone
3. Allow camera permissions when prompted

### Option 2: Same Network
1. Ensure phone and computer are on the same WiFi network
2. Find your computer's IP address: `ip addr show` or `ifconfig`
3. Visit `http://[YOUR_IP]:3000` on your phone

### Option 3: Manual ngrok Setup
```bash
# Install ngrok (if not already installed)
# Visit https://ngrok.com/download

# Start application
./start.sh

# In another terminal, expose the port
ngrok http 3000

# Use the ngrok URL on your phone
```

## 🔧 Development Setup

### Frontend Development
```bash
cd webrtc-vlm-frontend
pnpm install
pnpm run dev
```

### Backend Development
```bash
cd webrtc-vlm-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## 📊 Benchmarking

Run performance benchmarks to collect metrics:

```bash
# 30-second benchmark in server mode
./bench/run_bench.sh --duration 30 --mode server

# 60-second benchmark in WASM mode
./bench/run_bench.sh --duration 60 --mode wasm

# Custom output file
./bench/run_bench.sh --duration 30 --mode server --output my_metrics.json
```

The benchmark generates `metrics.json` with:
- Median & P95 end-to-end latency
- Server and network latency breakdown
- Processed FPS and bandwidth usage
- System resource utilization

## 🏗️ Architecture

### Frontend (React + Vite)
- **WebRTC Client**: Handles peer connections and media streams
- **Detection Overlay**: Renders bounding boxes on video canvas
- **Metrics Dashboard**: Real-time performance monitoring
- **Responsive UI**: Works on desktop and mobile

### Backend (Flask + SocketIO)
- **WebRTC Gateway**: Receives video tracks from clients
- **Object Detection**: YOLO-based inference pipeline
- **Metrics Collection**: Latency and performance tracking
- **CORS Enabled**: Supports cross-origin requests

### Processing Modes

#### WASM Mode (Low-Resource)
- Client-side inference using ONNX Runtime Web
- Reduced server load
- Input resolution: 320×240
- Target FPS: 10-15
- Suitable for modest hardware (Intel i5, 8GB RAM)

#### Server Mode (High-Performance)
- Server-side inference with full YOLO model
- Higher accuracy and performance
- Input resolution: 640×640
- Target FPS: 15-30
- Requires more server resources

## 📋 API Reference

### WebRTC Endpoints
- `POST /api/webrtc/offer` - Handle WebRTC offers
- `POST /api/webrtc/ice-candidate` - Handle ICE candidates
- `POST /api/webrtc/close` - Close connections

### SocketIO Events
- `detection_result` - Real-time detection results
- `metrics_update` - Performance metrics updates
- `connect/disconnect` - Connection status

### Detection Result Format
```json
{
  "frame_id": "string_or_int",
  "capture_ts": 1690000000000,
  "recv_ts": 1690000000100,
  "inference_ts": 1690000000120,
  "detections": [
    {
      "label": "person",
      "score": 0.93,
      "xmin": 0.12,
      "ymin": 0.08,
      "xmax": 0.34,
      "ymax": 0.67
    }
  ]
}
```

## 🔍 Troubleshooting

### Common Issues

#### Camera Not Working
- Check browser permissions for camera access
- Ensure HTTPS or localhost for WebRTC
- Try different browsers (Chrome recommended)

#### Phone Cannot Connect
- Verify both devices on same network
- Check firewall settings
- Use ngrok for external access
- Ensure ports 3000 and 5000 are accessible

#### Poor Performance
- Switch to WASM mode for lower resource usage
- Reduce video resolution in browser settings
- Close other applications to free resources
- Check network bandwidth

#### WebSocket Connection Failed
- Verify backend is running on port 5000
- Check CORS configuration
- Restart both frontend and backend

### Debug Commands
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test backend health
curl http://localhost:5000/api/health

# Check network connectivity
ping localhost
```

## 📈 Performance Optimization

### Low-Resource Recommendations
- Use WASM mode
- Reduce video resolution to 320×240
- Limit processing to 10-15 FPS
- Enable frame thinning/dropping
- Close unnecessary browser tabs

### High-Performance Setup
- Use server mode
- Increase video resolution to 640×640
- Target 15-30 FPS processing
- Use dedicated GPU (if available)
- Optimize network bandwidth

## 🔒 Security Considerations

- WebRTC requires HTTPS in production
- Implement proper authentication for production use
- Rate limiting for API endpoints
- Input validation for all user data
- Secure model file access

## 📦 Deployment

### Docker Production Deployment
```bash
# Build and start
docker-compose up --build -d

# Scale services
docker-compose up --scale backend=2 -d

# Update configuration
docker-compose down
docker-compose up -d
```

### Environment Variables
- `FLASK_ENV`: Set to 'production' for production
- `DETECTION_MODE`: Default processing mode
- `VITE_BACKEND_URL`: Backend URL for frontend

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit a pull request with detailed description

### Development Guidelines
- Follow existing code style
- Add tests for new features
- Update documentation
- Test on multiple browsers/devices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [YOLO](https://github.com/ultralytics/yolov5) for object detection models
- [ONNX Runtime](https://onnxruntime.ai/) for cross-platform inference
- [aiortc](https://github.com/aiortc/aiortc) for Python WebRTC implementation
- [React](https://reactjs.org/) and [Vite](https://vitejs.dev/) for frontend framework

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Include system information and logs

---

**Note**: This is a demonstration project. For production use, implement proper security measures, authentication, and error handling.

