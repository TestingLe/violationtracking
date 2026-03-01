import dlib
import cv2
import numpy as np
from config.config import PATHS

class FaceRecognizer:
    def __init__(self):
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor(PATHS['shape_predictor'])
        self.face_recognizer = dlib.face_recognition_model_v1(PATHS['face_recognizer'])
        self.known_faces = {}  # Store known face encodings
    
    def get_face_encodings(self, image):
        # Convert image to RGB (dlib uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = self.detector(rgb_image)
        encodings = []
        
        for face in faces:
            # Get facial landmarks
            shape = self.shape_predictor(rgb_image, face)
            
            # Get face encoding (128D vector)
            face_encoding = self.face_recognizer.compute_face_descriptor(rgb_image, shape)
            encodings.append(np.array(face_encoding))
        
        return encodings, faces
    
    def compare_faces(self, known_encoding, face_encoding, tolerance=0.6):
        # Calculate Euclidean distance between face encodings
        distance = np.linalg.norm(known_encoding - face_encoding)
        return distance < tolerance
    
    def recognize_face(self, image):
        encodings, faces = self.get_face_encodings(image)
        recognized_faces = []
        
        for encoding, face in zip(encodings, faces):
            for name, known_encoding in self.known_faces.items():
                if self.compare_faces(known_encoding, encoding):
                    recognized_faces.append((name, face))
                    break
        
        return recognized_faces
