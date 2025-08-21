import json
import asyncio
from flask import Blueprint, request, jsonify
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

webrtc_bp = Blueprint('webrtc', __name__)

# Global variables
peer_connections = {}
relay = MediaRelay()

@webrtc_bp.route('/offer', methods=['POST'])
def handle_offer():
    """
    Handle WebRTC offer from client
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        offer = data.get('offer')
        mode = data.get('mode', 'wasm')
        
        if not offer:
            return jsonify({'error': 'No offer provided'}), 400
        
        # Create peer connection
        pc = RTCPeerConnection()
        peer_connections[session_id] = pc
        
        # Handle incoming track
        @pc.on("track")
        async def on_track(track):
            print(f"Received track: {track.kind}")
            if track.kind == "video":
                # Import here to avoid circular imports
                from src.main import DetectionVideoStreamTrack
                
                # Create detection track
                detection_track = DetectionVideoStreamTrack(track, session_id, mode)
                
                # Add track to peer connection
                pc.addTrack(detection_track)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "closed":
                if session_id in peer_connections:
                    del peer_connections[session_id]
        
        # Set remote description
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process_offer():
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=offer['sdp'],
                type=offer['type']
            ))
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            return {
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            }
        
        answer = loop.run_until_complete(process_offer())
        
        return jsonify({
            'answer': answer,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error handling offer: {e}")
        return jsonify({'error': str(e)}), 500

@webrtc_bp.route('/ice-candidate', methods=['POST'])
def handle_ice_candidate():
    """
    Handle ICE candidate from client
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        candidate = data.get('candidate')
        
        if session_id not in peer_connections:
            return jsonify({'error': 'Session not found'}), 404
        
        pc = peer_connections[session_id]
        
        # Add ICE candidate
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def add_candidate():
            if candidate:
                await pc.addIceCandidate(candidate)
        
        loop.run_until_complete(add_candidate())
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error handling ICE candidate: {e}")
        return jsonify({'error': str(e)}), 500

@webrtc_bp.route('/close', methods=['POST'])
def handle_close():
    """
    Close WebRTC connection
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')
        
        if session_id in peer_connections:
            pc = peer_connections[session_id]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def close_connection():
                await pc.close()
            
            loop.run_until_complete(close_connection())
            del peer_connections[session_id]
        
        return jsonify({'status': 'closed'})
        
    except Exception as e:
        print(f"Error closing connection: {e}")
        return jsonify({'error': str(e)}), 500

