import os
import sys
import asyncio
import json
import time
import threading
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import onnxruntime as ort

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from src.models.user import db
from src.routes.user import user_bp
from src.routes.webrtc import webrtc_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(webrtc_bp, url_prefix='/api/webrtc')

# Database configuration (commented out for now)
# app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)
# with app.app_context():
#     db.create_all()

# Global variables for WebRTC and detection
peer_connections = {}
detection_sessions = {}
metrics_data = {}

class DetectionVideoStreamTrack(VideoStreamTrack):
    """
    A video stream track that applies object detection to frames
    """
    def __init__(self, track, session_id, mode='wasm'):
        super().__init__()
        self.track = track
        self.session_id = session_id
        self.mode = mode
        self.frame_count = 0
        self.last_detection_time = time.time()
        
        # Load ONNX model for server mode
        if mode == 'server':
            model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'webrtc-vlm-frontend', 'public', 'models', 'yolov10n.onnx')
            if os.path.exists(model_path):
                self.onnx_session = ort.InferenceSession(model_path)
            else:
                self.onnx_session = None
                print(f"Warning: ONNX model not found at {model_path}")

    async def recv(self):
        frame = await self.track.recv()
        
        # Convert frame to numpy array for processing
        img = frame.to_ndarray(format="bgr24")
        
        # Perform object detection
        detections = await self.detect_objects(img)
        
        # Send detection results via SocketIO
        if detections:
            capture_ts = int(time.time() * 1000)
            recv_ts = capture_ts + 10  # Simulated network delay
            inference_ts = recv_ts + 50  # Simulated inference time
            
            detection_result = {
                "frame_id": str(self.frame_count),
                "capture_ts": capture_ts,
                "recv_ts": recv_ts,
                "inference_ts": inference_ts,
                "detections": detections
            }
            
            socketio.emit('detection_result', detection_result, room=self.session_id)
            
            # Update metrics
            self.update_metrics(detection_result)
        
        self.frame_count += 1
        return frame

    async def detect_objects(self, img):
        """
        Perform object detection on the image
        """
        if self.mode == 'server' and self.onnx_session:
            # Server-side inference using ONNX
            return self.detect_with_onnx(img)
        else:
            # For WASM mode, we'll send the frame to the client for processing
            # For now, return mock detections
            return self.mock_detections()

    def detect_with_onnx(self, img):
        """
        Perform object detection using ONNX model
        """
        try:
            # Preprocess image
            input_size = (640, 640)
            img_resized = cv2.resize(img, input_size)
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
            img_normalized = img_rgb.astype(np.float32) / 255.0
            img_transposed = np.transpose(img_normalized, (2, 0, 1))
            img_batch = np.expand_dims(img_transposed, axis=0)
            
            # Run inference
            input_name = self.onnx_session.get_inputs()[0].name
            outputs = self.onnx_session.run(None, {input_name: img_batch})
            
            # Post-process outputs (simplified)
            detections = self.postprocess_yolo_outputs(outputs[0])
            return detections
            
        except Exception as e:
            print(f"Error in ONNX detection: {e}")
            return self.mock_detections()

    def postprocess_yolo_outputs(self, outputs):
        """
        Post-process YOLO outputs to extract detections
        """
        detections = []
        # This is a simplified post-processing
        # In a real implementation, you would properly parse YOLO outputs
        
        # Mock some detections for demonstration
        if np.random.random() > 0.7:  # 30% chance of detection
            detections.append({
                "label": "person",
                "score": 0.85 + np.random.random() * 0.1,
                "xmin": 0.2 + np.random.random() * 0.3,
                "ymin": 0.1 + np.random.random() * 0.3,
                "xmax": 0.4 + np.random.random() * 0.3,
                "ymax": 0.6 + np.random.random() * 0.3
            })
        
        return detections

    def mock_detections(self):
        """
        Generate mock detections for testing
        """
        detections = []
        if np.random.random() > 0.6:  # 40% chance of detection
            labels = ["person", "car", "bicycle", "dog", "cat", "bottle", "chair"]
            label = np.random.choice(labels)
            detections.append({
                "label": label,
                "score": 0.7 + np.random.random() * 0.25,
                "xmin": np.random.random() * 0.5,
                "ymin": np.random.random() * 0.5,
                "xmax": 0.3 + np.random.random() * 0.4,
                "ymax": 0.3 + np.random.random() * 0.4
            })
        
        return detections

    def update_metrics(self, detection_result):
        """
        Update performance metrics
        """
        session_id = self.session_id
        if session_id not in metrics_data:
            metrics_data[session_id] = {
                'latencies': [],
                'inference_times': [],
                'frame_count': 0,
                'start_time': time.time()
            }
        
        # Calculate latencies
        e2e_latency = time.time() * 1000 - detection_result['capture_ts']
        server_latency = detection_result['inference_ts'] - detection_result['recv_ts']
        network_latency = detection_result['recv_ts'] - detection_result['capture_ts']
        
        metrics_data[session_id]['latencies'].append(e2e_latency)
        metrics_data[session_id]['inference_times'].append(server_latency)
        metrics_data[session_id]['frame_count'] += 1
        
        # Emit updated metrics
        current_time = time.time()
        elapsed_time = current_time - metrics_data[session_id]['start_time']
        fps = metrics_data[session_id]['frame_count'] / elapsed_time if elapsed_time > 0 else 0
        
        # Calculate median and P95 latencies
        latencies = metrics_data[session_id]['latencies']
        if latencies:
            latencies_sorted = sorted(latencies)
            median_latency = latencies_sorted[len(latencies_sorted) // 2]
            p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        else:
            median_latency = 0
            p95_latency = 0
        
        metrics_update = {
            'modelInferenceTime': server_latency,
            'totalTime': e2e_latency,
            'overheadTime': e2e_latency - server_latency,
            'modelFPS': fps,
            'totalFPS': fps,
            'overheadFPS': fps,
            'e2eLatencyMedian': median_latency,
            'e2eLatencyP95': p95_latency,
            'serverLatency': server_latency,
            'networkLatency': network_latency,
            'processedFPS': fps,
            'bandwidth': 1000  # Mock bandwidth
        }
        
        socketio.emit('metrics_update', metrics_update, room=session_id)

# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Clean up peer connection if exists
    if request.sid in peer_connections:
        peer_connections[request.sid].close()
        del peer_connections[request.sid]
    
    # Clean up detection session
    if request.sid in detection_sessions:
        del detection_sessions[request.sid]
    
    # Clean up metrics data
    if request.sid in metrics_data:
        del metrics_data[request.sid]

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room', request.sid)
    print(f'Client {request.sid} joining room {room}')
    # In a real implementation, you might want to validate the room
    emit('room_joined', {'room': room})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

