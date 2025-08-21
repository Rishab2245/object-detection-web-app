from flask import Blueprint, request, jsonify
import onnxruntime as ort
import numpy as np
import cv2
import base64
import time
import json
import os

inference_bp = Blueprint('inference', __name__)

# Load YOLO classes
with open('data/yolo_classes.json', 'r') as f:
    yolo_classes = json.load(f)

# Global model session
model_session = None
current_model = None

def load_model(model_name):
    global model_session, current_model
    if current_model != model_name:
        model_path = f'models/{model_name}'
        if os.path.exists(model_path):
            model_session = ort.InferenceSession(model_path)
            current_model = model_name
            return True
    return model_session is not None

def preprocess_image(image_data, target_size):
    """Preprocess image for YOLO inference"""
    # Decode base64 image
    image_bytes = base64.b64decode(image_data.split('%2C')[1])
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Convert BGR to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Resize image
    resized = cv2.resize(image, target_size)
    
    # Normalize and transpose
    input_tensor = resized.astype(np.float32) / 255.0
    input_tensor = np.transpose(input_tensor, (2, 0, 1))  # HWC to CHW
    input_tensor = np.expand_dims(input_tensor, axis=0)  # Add batch dimension
    
    return input_tensor

def postprocess_yolov10(output, conf_threshold=0.25):
    """Postprocess YOLOv10 output"""
    detections = []
    
    # YOLOv10 output format: [1, num_detections, 6] where 6 = [x1, y1, x2, y2, score, class_id]
    for detection in output[0]:
        x1, y1, x2, y2, score, class_id = detection
        
        if score < conf_threshold:
            break
            
        # Convert to normalized coordinates [0, 1]
        detection_dict = {
            "label": yolo_classes[int(class_id)],
            "score": float(score),
            "xmin": float(x1),
            "ymin": float(y1),
            "xmax": float(x2),
            "ymax": float(y2)
        }
        detections.append(detection_dict)
    
    return detections

def postprocess_yolov7(output, conf_threshold=0.25):
    """Postprocess YOLOv7 output"""
    detections = []
    
    # YOLOv7 output format: [num_detections, 7] where 7 = [batch_id, x1, y1, x2, y2, class_id, score]
    for detection in output:
        batch_id, x1, y1, x2, y2, class_id, score = detection
        
        if score < conf_threshold:
            continue
            
        # Convert to normalized coordinates [0, 1]
        detection_dict = {
            "label": yolo_classes[int(class_id)],
            "score": float(score),
            "xmin": float(x1),
            "ymin": float(y1),
            "xmax": float(x2),
            "ymax": float(y2)
        }
        detections.append(detection_dict)
    
    return detections

@inference_bp.route('/detect', methods=['POST'])
def detect_objects():
    try:
        data = request.get_json()
        
        # Extract required fields
        frame_id = data.get('frame_id')
        capture_ts = data.get('capture_ts')
        image_data = data.get('image_data')
        model_name = data.get('model_name', 'yolov10n.onnx')
        resolution = data.get('resolution', [256, 256])
        
        recv_ts = int(time.time() * 1000)
        
        # Load model if needed
        if not load_model(model_name):
            return jsonify({'error': 'Failed to load model'}), 500
        
        # Preprocess image
        input_tensor = preprocess_image(image_data, tuple(resolution))
        
        # Run inference
        inference_start = time.time()
        input_name = model_session.get_inputs()[0].name
        output = model_session.run(None, {input_name: input_tensor})[0]
        inference_ts = int(time.time() * 1000)
        
        # Postprocess based on model type
        if 'yolov10' in model_name:
            detections = postprocess_yolov10(output)
        else:
            detections = postprocess_yolov7(output)
        
        # Prepare response
        response = {
            "frame_id": frame_id,
            "capture_ts": capture_ts,
            "recv_ts": recv_ts,
            "inference_ts": inference_ts,
            "detections": detections
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inference_bp.route('/models', methods=['GET'])
def get_available_models():
    """Get list of available models"""
    try:
        models = []
        if os.path.exists('models'):
            for file in os.listdir('models'):
                if file.endswith('onnx'):
                    models.append(file)
        return jsonify({'models': models})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inference_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'current_model': current_model})
