#!/usr/bin/env python3
"""
YOLOv8 Uniform Detection API Server
Provides REST endpoints for uniform management and real-time detection.
"""

import os
import sys
import json
import uuid
import base64
import time
from io import BytesIO
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import ultralytics for YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARNING] YOLO not available")

# Import MySQL
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("[WARNING] MySQL not available")

# Import hashlib for password hashing
import hashlib

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db_connection():
    """Get MySQL database connection"""
    if not MYSQL_AVAILABLE:
        return None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='violation_tracker'
        )
        return connection
    except Error as e:
        print(f"[ERROR] MySQL connection: {e}")
        return None

# ─── Configuration ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UNIFORMS_DIR = os.path.join(BASE_DIR, 'uniforms')
UNIFORMS_DB = os.path.join(UNIFORMS_DIR, 'uniforms.json')

os.makedirs(UNIFORMS_DIR, exist_ok=True)

# ─── Flask App ───────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

# ─── YOLOv8 Model ───────────────────────────────────────────────────────────

if YOLO_AVAILABLE:
    print("[INFO] Loading YOLOv8 model...")
    model = YOLO('yolov8n.pt')  # nano model for speed
    print("[INFO] YOLOv8 model loaded successfully!")
else:
    model = None
    print("[WARNING] YOLOv8 model not available")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_uniforms_db():
    """Load uniform profiles from the JSON database."""
    if os.path.exists(UNIFORMS_DB):
        with open(UNIFORMS_DB, 'r') as f:
            return json.load(f)
    return []

def save_uniforms_db(data):
    """Persist uniform profiles to JSON."""
    with open(UNIFORMS_DB, 'w') as f:
        json.dump(data, f, indent=2)

def base64_to_cv2(b64_string):
    """Convert a base64-encoded image string to an OpenCV BGR image."""
    if ',' in b64_string:
        b64_string = b64_string.split(',')[1]
    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def cv2_to_base64(img):
    """Convert an OpenCV BGR image to a base64 JPEG string."""
    _, buf = cv2.imencode('.jpg', img)
    return base64.b64encode(buf).decode('utf-8')

def extract_clothing_region(img, box):
    """
    Given a person bounding box [x1, y1, x2, y2],
    extract the torso/clothing region (middle 60% vertically, inner 70% horizontally).
    """
    x1, y1, x2, y2 = map(int, box)
    h = y2 - y1
    w = x2 - x1

    # Torso region: skip top 25% (head), take next 45% (torso)
    torso_y1 = y1 + int(h * 0.25)
    torso_y2 = y1 + int(h * 0.70)
    # Narrow horizontally to avoid arms/background
    torso_x1 = x1 + int(w * 0.15)
    torso_x2 = x2 - int(w * 0.15)

    # Clamp to image bounds
    ih, iw = img.shape[:2]
    torso_y1 = max(0, min(torso_y1, ih))
    torso_y2 = max(0, min(torso_y2, ih))
    torso_x1 = max(0, min(torso_x1, iw))
    torso_x2 = max(0, min(torso_x2, iw))

    if torso_y2 - torso_y1 < 10 or torso_x2 - torso_x1 < 10:
        return None

    return img[torso_y1:torso_y2, torso_x1:torso_x2]

def compute_color_histogram(img):
    """Compute a normalized HSV color histogram for an image region."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist

def compare_uniforms(hist, saved_uniforms):
    """
    Compare a clothing histogram against all saved uniform profiles.
    Returns the best match (name, confidence) or None.
    """
    best_match = None
    best_score = 0.0

    for uniform in saved_uniforms:
        hist_path = os.path.join(UNIFORMS_DIR, uniform['hist_file'])
        if not os.path.exists(hist_path):
            continue

        saved_hist = np.load(hist_path)
        # Correlation comparison: 1.0 = perfect match
        score = cv2.compareHist(hist, saved_hist.astype(np.float32), cv2.HISTCMP_CORREL)

        if score > best_score:
            best_score = score
            best_match = uniform

    if best_match and best_score > 0.3:
        return {
            'name': best_match['name'],
            'confidence': round(float(best_score) * 100, 1),
            'id': best_match['id']
        }
    return None

# ─── API Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)

# ── Save Uniform (from camera frame) ────────────────────────────────────────

@app.route('/api/uniforms', methods=['POST'])
def save_uniform():
    """
    Save a new uniform profile from a camera frame.
    Expects JSON: { name, description, frame (base64) }
    YOLOv8 detects the person, extracts clothing region, saves histogram.
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        frame_b64 = data.get('frame', '')

        if not name:
            return jsonify({'error': 'Uniform name is required'}), 400
        if not frame_b64:
            return jsonify({'error': 'Camera frame is required'}), 400

        # Decode frame
        img = base64_to_cv2(frame_b64)
        if img is None:
            return jsonify({'error': 'Invalid image data'}), 400

        # Run YOLOv8 person detection
        results = model(img, classes=[0], conf=0.5, verbose=False)

        persons = []
        for r in results:
            for box in r.boxes:
                persons.append(box.xyxy[0].cpu().numpy())

        if len(persons) == 0:
            return jsonify({'error': 'No person detected in frame. Please make sure you are visible in the camera.'}), 400

        # Use the largest person detection (most prominent)
        largest_box = max(persons, key=lambda b: (b[2]-b[0]) * (b[3]-b[1]))

        # Extract clothing region
        clothing = extract_clothing_region(img, largest_box)
        if clothing is None:
            return jsonify({'error': 'Could not extract clothing region. Try standing further from the camera.'}), 400

        # Compute color histogram
        hist = compute_color_histogram(clothing)

        # Generate unique ID
        uniform_id = str(uuid.uuid4())[:8]

        # Save reference image (the clothing crop)
        img_filename = f'{uniform_id}_ref.jpg'
        cv2.imwrite(os.path.join(UNIFORMS_DIR, img_filename), clothing)

        # Save full frame thumbnail
        thumb_filename = f'{uniform_id}_thumb.jpg'
        thumb = cv2.resize(img, (320, 240))
        cv2.imwrite(os.path.join(UNIFORMS_DIR, thumb_filename), thumb)

        # Save histogram
        hist_filename = f'{uniform_id}_hist.npy'
        np.save(os.path.join(UNIFORMS_DIR, hist_filename), hist)

        # Update database
        uniforms = load_uniforms_db()
        uniform_entry = {
            'id': uniform_id,
            'name': name,
            'description': description,
            'img_file': img_filename,
            'thumb_file': thumb_filename,
            'hist_file': hist_filename,
            'created_at': datetime.now().isoformat(),
            'dominant_colors': get_dominant_colors(clothing)
        }
        uniforms.append(uniform_entry)
        save_uniforms_db(uniforms)

        return jsonify({
            'success': True,
            'uniform': uniform_entry,
            'message': f'Uniform "{name}" saved successfully!'
        })

    except Exception as e:
        print(f"[ERROR] save_uniform: {e}")
        return jsonify({'error': str(e)}), 500

def get_dominant_colors(img, k=3):
    """Extract k dominant colors from an image using K-means clustering."""
    pixels = img.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(int)
    # Count occurrences and sort by frequency
    counts = np.bincount(labels.flatten())
    sorted_indices = np.argsort(-counts)
    colors = []
    for idx in sorted_indices:
        b, g, r = centers[idx]
        pct = round(counts[idx] / len(labels) * 100, 1)
        colors.append({'r': int(r), 'g': int(g), 'b': int(b), 'percentage': pct})
    return colors

# ── List Uniforms ────────────────────────────────────────────────────────────

@app.route('/api/uniforms', methods=['GET'])
def list_uniforms():
    """Return all saved uniform profiles."""
    uniforms = load_uniforms_db()
    return jsonify({'uniforms': uniforms})

# ── Delete Uniform ───────────────────────────────────────────────────────────

@app.route('/api/uniforms/<uniform_id>', methods=['DELETE'])
def delete_uniform(uniform_id):
    """Delete a uniform profile and its associated files."""
    uniforms = load_uniforms_db()
    target = None
    for u in uniforms:
        if u['id'] == uniform_id:
            target = u
            break

    if not target:
        return jsonify({'error': 'Uniform not found'}), 404

    # Delete files
    for key in ['img_file', 'thumb_file', 'hist_file']:
        fpath = os.path.join(UNIFORMS_DIR, target.get(key, ''))
        if os.path.exists(fpath):
            os.remove(fpath)

    uniforms = [u for u in uniforms if u['id'] != uniform_id]
    save_uniforms_db(uniforms)

    return jsonify({'success': True, 'message': f'Uniform "{target["name"]}" deleted.'})

# ── Detect Uniform (from camera frame) ──────────────────────────────────────

@app.route('/api/detect', methods=['POST'])
def detect_uniform():
    """
    Run YOLOv8 person detection on a camera frame and match clothing
    against saved uniform profiles.
    Expects JSON: { frame (base64) }
    Returns: { detections: [{ box, person_conf, uniform_match, clothing_region }] }
    """
    try:
        data = request.get_json()
        frame_b64 = data.get('frame', '')

        if not frame_b64:
            return jsonify({'error': 'Frame is required'}), 400

        img = base64_to_cv2(frame_b64)
        if img is None:
            return jsonify({'error': 'Invalid image data'}), 400

        # Run YOLOv8
        results = model(img, classes=[0], conf=0.4, verbose=False)

        uniforms = load_uniforms_db()
        detections = []

        for r in results:
            for box in r.boxes:
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0])

                # Extract clothing region
                clothing = extract_clothing_region(img, xyxy)
                uniform_match = None

                if clothing is not None and len(uniforms) > 0:
                    hist = compute_color_histogram(clothing)
                    uniform_match = compare_uniforms(hist, uniforms)

                x1, y1, x2, y2 = map(int, xyxy)
                detections.append({
                    'box': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
                    'person_confidence': round(conf * 100, 1),
                    'uniform_match': uniform_match,
                    'is_compliant': uniform_match is not None and uniform_match['confidence'] > 50
                })

        return jsonify({
            'detections': detections,
            'total_persons': len(detections),
            'total_uniforms_saved': len(uniforms)
        })

    except Exception as e:
        print(f"[ERROR] detect_uniform: {e}")
        return jsonify({'error': str(e)}), 500

# ── Violation Logging ────────────────────────────────────────────────────────

VIOLATION_LOG_DIR = os.path.join(BASE_DIR, '..', 'ViolationLogs')
os.makedirs(VIOLATION_LOG_DIR, exist_ok=True)

@app.route('/api/violation-log', methods=['POST'])
def save_violation_log():
    """
    Save a violation screenshot with overlaid violation text and timestamp.
    Expects JSON: { frame (base64), violations (list of strings), studentInfo (object) }
    """
    try:
        data = request.get_json()
        frame_b64 = data.get('frame', '')
        violations = data.get('violations', [])
        student_info = data.get('studentInfo', {})

        if not frame_b64:
            return jsonify({'error': 'Frame is required'}), 400
        if not violations:
            return jsonify({'error': 'No violations provided'}), 400

        img = base64_to_cv2(frame_b64)
        if img is None:
            return jsonify({'error': 'Invalid image data'}), 400

        h, w = img.shape[:2]

        # Draw dark overlay bar at the bottom
        bar_height = 30 + len(violations) * 28
        if student_info:
            bar_height += 40  # Extra space for student info
        overlay = img.copy()
        cv2.rectangle(overlay, (0, h - bar_height), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        # Draw date/time
        now = datetime.now()
        date_str = now.strftime('%B %d, %Y  %I:%M:%S %p')
        cv2.putText(img, date_str, (12, h - bar_height + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 212, 255), 1, cv2.LINE_AA)

        # Draw student info if available
        y_offset = h - bar_height + 50
        if student_info:
            student_text = f"Student: {student_info.get('name', 'Unknown')} ({student_info.get('id', 'Unknown')})"
            cv2.putText(img, student_text, (12, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            class_text = f"Class: {student_info.get('class', 'Unknown')} {student_info.get('section', '')} | Gender: {student_info.get('gender', 'Unknown')}"
            cv2.putText(img, class_text, (12, y_offset + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
            y_offset += 40

        # Draw each violation
        for i, violation in enumerate(violations):
            text = f">> {violation}"
            cv2.putText(img, text, (12, y_offset + i * 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (68, 68, 255), 1, cv2.LINE_AA)

        # Draw "VIOLATION" label at top-left
        cv2.rectangle(img, (0, 0), (180, 32), (0, 0, 200), -1)
        cv2.putText(img, 'VIOLATION', (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        # Save to ViolationLogs folder
        filename = f"violation_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(VIOLATION_LOG_DIR, filename)
        cv2.imwrite(filepath, img)

        print(f"[VIOLATION] Saved: {filename} — {violations}")

        return jsonify({
            'success': True,
            'filename': filename,
            'violations': violations,
            'studentInfo': student_info,
            'timestamp': date_str
        })

    except Exception as e:
        print(f"[ERROR] save_violation_log: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/violation-logs', methods=['GET'])
def list_violation_logs():
    """List all saved violation log images."""
    logs = []
    if os.path.exists(VIOLATION_LOG_DIR):
        for f in sorted(os.listdir(VIOLATION_LOG_DIR), reverse=True):
            if f.endswith('.jpg') or f.endswith('.png'):
                logs.append({
                    'filename': f,
                    'path': f'/ViolationLogs/{f}',
                    'timestamp': f.replace('violation_', '').replace('.jpg', '').replace('.png', '')
                })
    return jsonify({'logs': logs})

@app.route('/ViolationLogs/<path:filename>')
def serve_violation_log(filename):
    return send_from_directory(VIOLATION_LOG_DIR, filename)

# ─── In-Memory User Storage (for testing when MySQL is not available) ───

TEST_USERS = []  # List of {id, username, password_hash}

def get_next_user_id():
    """Get next available user ID"""
    if TEST_USERS:
        return max(user['id'] for user in TEST_USERS) + 1
    return 1

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint for web interface"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if not MYSQL_AVAILABLE:
        # Use in-memory storage for testing
        hashed_password = hash_password(password)
        user = next((u for u in TEST_USERS if u['username'] == username and u['password_hash'] == hashed_password), None)
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username']
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username FROM users WHERE username = %s AND password = %s",
            (username, hash_password(password))
        )
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username']
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/signup', methods=['POST'])
def signup():
    """Signup endpoint for web interface"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    if not MYSQL_AVAILABLE:
        # Use in-memory storage for testing
        # Check if username already exists
        existing_user = next((u for u in TEST_USERS if u['username'] == username), None)
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create new user
        user_id = get_next_user_id()
        hashed_password = hash_password(password)
        new_user = {
            'id': user_id,
            'username': username,
            'password_hash': hashed_password
        }
        TEST_USERS.append(new_user)
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': username
            },
            'message': 'Account created successfully'
        })
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create new user
        hashed_password = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_password)
        )
        connection.commit()
        
        # Get the new user ID
        user_id = cursor.lastrowid
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': username
            },
            'message': 'Account created successfully'
        })
        
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# ─── Violations API ──────────────────────────────────────────────────────────

@app.route('/api/violations', methods=['GET'])
def get_violations():
    """Get all violations from database"""
    if not MYSQL_AVAILABLE:
        # Return empty list for testing
        return jsonify({'violations': []})
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                v.id,
                u.username AS student_name,
                v.violation_type,
                v.description,
                v.gender,
                v.timestamp,
                v.reported_by
            FROM violations v
            JOIN users u ON u.id = v.user_id
            ORDER BY v.timestamp DESC
        """)
        violations = cursor.fetchall()
        
        return jsonify({'violations': violations})
        
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/violations/<int:violation_id>/receipt', methods=['GET'])
def generate_receipt(violation_id):
    """Generate a printable receipt for a violation"""
    if not MYSQL_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 500
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                v.id,
                u.username AS student_name,
                v.violation_type,
                v.description,
                v.gender,
                v.timestamp,
                v.reported_by
            FROM violations v
            JOIN users u ON u.id = v.user_id
            WHERE v.id = %s
        """, (violation_id,))
        violation = cursor.fetchone()
        
        if not violation:
            return jsonify({'error': 'Violation not found'}), 404
        
        # Generate HTML receipt
        receipt_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Violation Receipt</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 400px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 2px solid #000;
                    background: #f9f9f9;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #000;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                .school-name {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .receipt-title {{
                    font-size: 16px;
                    color: #666;
                }}
                .violation-details {{
                    margin: 20px 0;
                }}
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    margin: 8px 0;
                    padding: 5px 0;
                    border-bottom: 1px solid #ddd;
                }}
                .label {{
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
                .print-btn {{
                    display: none;
                }}
                @media print {{
                    .print-btn {{
                        display: none;
                    }}
                    body {{
                        border: none;
                        background: white;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="school-name">SCHOOL VIOLATION RECEIPT</div>
                <div class="receipt-title">Official Violation Notice</div>
            </div>
            
            <div class="violation-details">
                <div class="detail-row">
                    <span class="label">Violation ID:</span>
                    <span>{violation['id']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Student Name:</span>
                    <span>{violation['student_name']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Gender:</span>
                    <span>{violation['gender']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Violation Type:</span>
                    <span>{violation['violation_type']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span>{violation['description']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Date/Time:</span>
                    <span>{violation['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Reported By:</span>
                    <span>{violation['reported_by']}</span>
                </div>
            </div>
            
            <div class="footer">
                <p>This is an official notice of school policy violation.</p>
                <p>Please contact school administration for further information.</p>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <button class="print-btn" onclick="window.print()">Print Receipt</button>
        </body>
        </html>
        """
        
        return receipt_html, 200, {'Content-Type': 'text/html'}
        
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  YOLOv8 Uniform Detection API Server")
    print("  Open: http://localhost:5000/uniform.html")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
