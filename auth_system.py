import os
import cv2
import numpy as np
import hashlib
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    mysql = None
    Error = Exception
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                              QPushButton, QMessageBox, QDialog, QHBoxLayout, QComboBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

def get_available_cameras(max_cameras=5):
    """Detect available cameras"""
    available = []
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append(i)
            cap.release()
    return available if available else [0]

# Lazy load dlib
dlib = None
def get_dlib():
    global dlib
    if dlib is None:
        try:
            import dlib as dlib_module
            dlib = dlib_module
        except ImportError:
            raise ImportError("dlib not installed - face recognition features unavailable")

class FaceRecognizer:
    def __init__(self):
        get_dlib()  # Lazy load dlib at first use
        self.face_detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        self.face_recognizer = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
        self.known_faces = {}
        self.load_known_faces()

    def get_face_encoding(self, image):
        try:
            # dlib face detector works best with RGB images (input is already RGB from cv2.cvtColor)
            # Use upsample_num_times=1 to detect smaller/farther faces
            faces = self.face_detector(image, 1)
            
            if len(faces) == 0:
                return None
                
            # Get the first face
            face = faces[0]
            
            # Get facial landmarks using RGB image
            shape = self.shape_predictor(image, face)
            
            # Get face encoding
            face_encoding = self.face_recognizer.compute_face_descriptor(image, shape)
            return np.array(face_encoding)
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return None

    def load_known_faces(self):
        connection = None
        cursor = None
        try:
            connection = self.get_db_connection()
            if connection is None:
                return
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, username, face_encoding FROM users WHERE face_encoding IS NOT NULL")
            
            for row in cursor.fetchall():
                if row.get('face_encoding') is None:
                    continue
                face_encoding = np.frombuffer(row['face_encoding'], dtype=np.float64)
                self.known_faces[row['id']] = {
                    'username': row['username'],
                    'encoding': face_encoding
                }
                
        except Error as e:
            print(f"Error loading known faces: {e}")
        except Exception as e:
            print(f"Error loading known faces: {e}")
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                if connection is not None:
                    connection.close()

    def recognize_face(self, face_encoding):
        if not self.known_faces:
            return None
            
        face_distances = []
        for user_id, data in self.known_faces.items():
            dist = np.linalg.norm(data['encoding'] - face_encoding)
            face_distances.append((user_id, dist))
            
        if not face_distances:
            return None
            
        # Get the best match
        best_match = min(face_distances, key=lambda x: x[1])
        
        # If the distance is less than 0.6, it's a match
        if best_match[1] < 0.6:
            return best_match[0]
        return None

    @staticmethod
    def get_db_connection():
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='violation_tracker'
            )
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None

class LoginWindow(QDialog):
    login_success = pyqtSignal(int, str)  # user_id, username
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.face_recognizer = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Login")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        
        # Face login button
        face_login_btn = QPushButton("Login with Face ID")
        face_login_btn.clicked.connect(self.handle_face_login)
        
        # Sign up button
        signup_btn = QPushButton("Create New Account")
        signup_btn.clicked.connect(self.show_signup)
        
        # Add widgets to layout
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_input)
        layout.addWidget(login_btn)
        layout.addWidget(QLabel("Or"))
        layout.addWidget(face_login_btn)
        layout.addWidget(QLabel("Don't have an account?"))
        layout.addWidget(signup_btn)
        
        self.setLayout(layout)
    
    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
            
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='violation_tracker'
            )
            if connection:
                cursor = connection.cursor(dictionary=True)
                # First, get the user by username
                cursor.execute(
                    "SELECT id, username, password FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()
                
                # Then verify the password
                if user and (user['password'] == password or user['password'] == hash_password(password)):
                    self.login_success.emit(user['id'], user['username'])
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Invalid username or password")
                    
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Error: {e}")
        finally:
            if 'connection' in locals() and connection is not None and connection.is_connected():
                cursor.close()
                connection.close()
    
    def handle_face_login(self):
        if self.face_recognizer is None:
            try:
                self.face_recognizer = FaceRecognizer()
            except Exception as e:
                QMessageBox.critical(self, "Face Login Error", f"Face recognition failed to initialize: {e}")
                return
        self.face_login_window = FaceLoginWindow(self.face_recognizer, self)
        self.face_login_window.login_success.connect(self.face_login_success)
        self.face_login_window.show()
    
    def face_login_success(self, user_id, username):
        self.login_success.emit(user_id, username)
        self.accept()
    
    def show_signup(self):
        if self.face_recognizer is None:
            try:
                self.face_recognizer = FaceRecognizer()
            except Exception as e:
                QMessageBox.critical(self, "Signup Error", f"Face recognition failed to initialize: {e}")
                return
        self.signup_window = SignupWindow(self.face_recognizer, self)
        self.signup_window.signup_success.connect(self.on_signup_success)
        self.signup_window.show()
    
    def on_signup_success(self, username):
        self.username_input.setText(username)
        self.password_input.setFocus()

class SignupWindow(QDialog):
    signup_success = pyqtSignal(str)  # username
    
    def __init__(self, face_recognizer, parent=None):
        super().__init__(parent)
        self.face_recognizer = face_recognizer
        self.cap = None
        self.current_camera = 0
        self.face_encoding = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Create Account")
        self.setFixedSize(500, 500)
        
        layout = QVBoxLayout()
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Choose a password")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Confirm Password
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self.available_cameras = get_available_cameras()
        for cam_id in self.available_cameras:
            self.camera_combo.addItem(f"Camera {cam_id}", cam_id)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        
        # Webcam feed for face registration
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(320, 240)
        self.camera_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setScaledContents(False)
        
        # Capture face button
        self.capture_btn = QPushButton("Register Face")
        self.capture_btn.clicked.connect(self.capture_face)
        
        # Sign up button
        signup_btn = QPushButton("Create Account")
        signup_btn.clicked.connect(self.handle_signup)
        
        # Add widgets to layout
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Confirm Password:"))
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(QLabel("Register your face:"))
        layout.addLayout(camera_layout)
        layout.addWidget(self.camera_label, 0, Qt.AlignCenter)
        layout.addWidget(self.capture_btn, 0, Qt.AlignCenter)
        layout.addWidget(signup_btn)
        
        self.setLayout(layout)
        
        # Start webcam
        self.start_camera(self.current_camera)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
    
    def start_camera(self, camera_id):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.cap = cv2.VideoCapture(camera_id)
        self.current_camera = camera_id
    
    def change_camera(self, index):
        camera_id = self.camera_combo.itemData(index)
        if camera_id is not None:
            self.start_camera(camera_id)
    
    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_label.setPixmap(scaled_pixmap)
    
    def capture_face(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert to RGB for face recognition
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.face_encoding = self.face_recognizer.get_face_encoding(rgb_image)
            
            if self.face_encoding is not None:
                QMessageBox.information(self, "Success", "Face captured successfully!")
            else:
                QMessageBox.warning(self, "Error", "No face detected. Please try again.")
    
    def handle_signup(self):
        username = self.username_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
            
        if self.face_encoding is None:
            QMessageBox.warning(self, "Error", "Please register your face")
            return
            
        try:
            connection = self.face_recognizer.get_db_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                
                # Check if username already exists
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    QMessageBox.warning(self, "Error", "Username already exists")
                    return
                
                # Insert new user
                face_encoding_bytes = self.face_encoding.tobytes()
                cursor.execute(
                    "INSERT INTO users (username, password, face_encoding) VALUES (%s, %s, %s)",
                    (username, hash_password(password), face_encoding_bytes)
                )
                user_id = cursor.lastrowid
                
                # Update the known faces
                self.face_recognizer.known_faces[user_id] = {
                    'username': username,
                    'encoding': self.face_encoding
                }
                
                connection.commit()
                cursor.close()
                connection.close()
                
                QMessageBox.information(self, "Success", "Account created successfully!")
                self.signup_success.emit(username)
                self.accept()
            else:
                QMessageBox.critical(self, "Database Error", "Could not connect to database. Please make sure MySQL is running.")
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Error: {e}")
    
    def closeEvent(self, event):
        # Release the camera when window is closed
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        event.accept()

class FaceLoginWindow(QDialog):
    login_success = pyqtSignal(int, str)  # user_id, username
    
    def __init__(self, face_recognizer, parent=None):
        super().__init__(parent)
        self.face_recognizer = face_recognizer
        self.cap = None
        self.current_camera = 0
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Face Login")
        self.setFixedSize(500, 450)
        
        layout = QVBoxLayout()
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Camera:"))
        self.camera_combo = QComboBox()
        self.available_cameras = get_available_cameras()
        for cam_id in self.available_cameras:
            self.camera_combo.addItem(f"Camera {cam_id}", cam_id)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addStretch()
        
        # Webcam feed
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(320, 240)
        self.camera_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setScaledContents(False)
        
        # Status label
        self.status_label = QLabel("Position your face in the frame")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Add widgets to layout
        layout.addLayout(camera_layout)
        layout.addWidget(self.camera_label, 0, Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Start webcam
        self.start_camera(self.current_camera)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.recognize_face)
        self.timer.start(30)
    
    def start_camera(self, camera_id):
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.cap = cv2.VideoCapture(camera_id)
        self.current_camera = camera_id
    
    def change_camera(self, index):
        camera_id = self.camera_combo.itemData(index)
        if camera_id is not None:
            self.start_camera(camera_id)
    
    def recognize_face(self):
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # Convert to RGB for face recognition
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get face encoding
        face_encoding = self.face_recognizer.get_face_encoding(rgb_image)
        
        if face_encoding is not None:
            # Try to recognize the face
            user_id = self.face_recognizer.recognize_face(face_encoding)
            
            if user_id is not None:
                # Face recognized
                self.timer.stop()
                self.cap.release()
                
                # Get username from known_faces
                username = self.face_recognizer.known_faces[user_id]['username']
                self.login_success.emit(user_id, username)
                self.accept()
                return
            else:
                self.status_label.setText("Face not recognized. Please try again.")
        else:
            self.status_label.setText("No face detected. Please position your face in the frame.")
        
        # Display the frame
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
    def closeEvent(self, event):
        # Release the camera when window is closed
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        event.accept()

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_tables():
    """Create necessary database tables if they don't exist"""
    # Check if MySQL is available
    try:
        import mysql.connector
        mysql_available = True
    except ImportError:
        mysql_available = False
        print("[INFO] MySQL not available - skipping database table creation")
        return False
    
    if not mysql_available:
        print("[INFO] MySQL not available - skipping database table creation")
        return False
        
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''
        )
        
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS violation_tracker")
        cursor.execute("USE violation_tracker")
        
        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            face_encoding LONGBLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create violations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            violation_type VARCHAR(100) NOT NULL,
            description TEXT,
            gender VARCHAR(10) DEFAULT 'Unknown',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reported_by VARCHAR(50) DEFAULT 'System',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        try:
            cursor.execute("ALTER TABLE violations ADD COLUMN reported_by VARCHAR(50) DEFAULT 'System'")
        except mysql.connector.Error:
            pass
        
        connection.commit()
        print("Database tables created successfully")
        return True
        
    except mysql.connector.Error as e:
        print(f"Error creating database tables: {e}")
        print("[INFO] Falling back to file-based storage")
        return False
    finally:
        if 'connection' in locals() and connection is not None and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    # Create database tables if they don't exist
    create_tables()
    
    # Run a simple test
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test login window
    login_window = LoginWindow()
    login_window.show()
    
    sys.exit(app.exec_())
