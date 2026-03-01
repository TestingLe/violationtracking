"# Student Violation Tracking System

A comprehensive system for tracking student uniform and appearance violations using computer vision and face recognition.

## Features

### Desktop Application (PyQt5)
- Real-time face detection and violation monitoring
- Automatic violation detection for hair style, uniform, and appearance
- Gender-specific violation rules:
  - **Boys**: Hair cut, hair color (must be black), necktie, uniform violations
  - **Girls**: Hair color (must be black), uniform violations
- Manual violation logging with gender selection
- MySQL database integration with fallback to JSON files
- User authentication system

### Web Dashboard
- Admin login system
- View all violations with statistics
- Generate printable receipts for students
- Real-time violation monitoring

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up MySQL database:
```bash
python init_db.py
```

3. Download required models (optional - for face recognition):
```bash
python download_face_model.py
python download_landmarks.py
```

## Usage

### Desktop Application
```bash
python main.py
```

### Web Dashboard
1. Start the web server:
```bash
python web/uniform_api.py
```

2. Open your browser and go to:
- Dashboard: `http://localhost:5000/admin.html`
- Real-time detection: `http://localhost:5000/index.html`

### Default Admin Credentials
- Username: `admin`
- Password: `admin123`

## Violation Types

### Hair Violations
- Fringe/bangs covering eyebrows
- Hair not combed neatly
- Long hair not tied/braided (girls)
- Hair cut violations (boys)
- Hair color not black

### Uniform Violations
- Necktie not properly worn (boys)
- Uniform not compliant

## API Endpoints

- `POST /api/login` - Admin authentication
- `GET /api/violations` - Get all violations
- `GET /api/violations/{id}/receipt` - Generate printable receipt
- `POST /api/violation-log` - Log violation with image
- `GET /api/violation-logs` - Get violation logs

## Requirements

- Python 3.7+
- PyQt5
- OpenCV
- MySQL
- Flask
- dlib (optional, for face recognition)
- YOLOv8 (for uniform detection)

## License

This project is for educational purposes." 
