#!/usr/bin/env python3
"""
Student Violation Tracking System with Authentication and Face Recognition
Enhanced with user accounts, face login, and violation tracking
"""

import sys
import cv2
import numpy as np
import imutils
import os
import time
import json
from imutils import face_utils
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QTextEdit,
                              QLineEdit, QMessageBox, QComboBox, QFrame,
                              QGraphicsDropShadowEffect, QScrollArea, QGroupBox,
                              QDialog, QStackedWidget)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QPainter, QPen, QIcon

# Lazy load dlib
dlib = None
def get_dlib():
    global dlib
    if dlib is None:
        try:
            import dlib as dlib_module
            dlib = dlib_module
        except ImportError:
            print("[WARNING] dlib not installed - face detection disabled")
    return dlib

# Import authentication system
from auth_system import LoginWindow, create_tables

# Try to import MySQL, but don't fail if not available
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("[WARNING] MySQL not available - using simplified mode")

# Create database tables if they don't exist
# Temporarily disabled due to MySQL connection issues
# if MYSQL_AVAILABLE:
#     result = create_tables()
#     print(f"[DEBUG] create_tables() returned: {result}")
#     if not result:
#         MYSQL_AVAILABLE = False
#         print("[INFO] MySQL database initialization failed - using file-based storage")
# else:
#     print("[INFO] MySQL not available - using file-based storage")
print("[INFO] Using file-based storage for violations")

class StudentInfoDialog(QDialog):
    """Dialog for collecting student information before violation detection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Student Information")
        self.setModal(True)
        self.setFixedSize(600, 700)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0c0c17, stop:0.5 #1a1a2e, stop:1 #16213e);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: 500;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: 800;
                color: #ffffff;
                text-align: center;
                margin-bottom: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            QLineEdit, QComboBox {
                background: rgba(30, 30, 45, 0.8);
                color: #ffffff;
                border: 2px solid #3a3a4e;
                border-radius: 8px;
                padding: 12px 18px;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #6a11cb;
                box-shadow: 0 0 0 2px rgba(106, 17, 203, 0.3);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7d2ae8, stop:1 #3a86ff);
                transform: translateY(-2px);
            }
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Student Information")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Form fields
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Name
        name_layout = QVBoxLayout()
        name_label = QLabel("Full Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter student's full name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        form_layout.addLayout(name_layout)
        
        # Strand
        strand_layout = QVBoxLayout()
        strand_label = QLabel("Strand:")
        self.strand_combo = QComboBox()
        self.strand_combo.addItems([
            "Select Strand",
            "STEM (Science, Technology, Engineering, Mathematics)",
            "ABM (Accountancy, Business, Management)",
            "HUMSS (Humanities and Social Sciences)",
            "GAS (General Academic Strand)",
            "TVL (Technical-Vocational-Livelihood)",
            "Arts and Design",
            "Sports"
        ])
        strand_layout.addWidget(strand_label)
        strand_layout.addWidget(self.strand_combo)
        form_layout.addLayout(strand_layout)
        
        # Age
        age_layout = QVBoxLayout()
        age_label = QLabel("Age:")
        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("Enter age")
        age_layout.addWidget(age_label)
        age_layout.addWidget(self.age_input)
        form_layout.addLayout(age_layout)
        
        # Email
        email_layout = QVBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        form_layout.addLayout(email_layout)
        
        # Phone Number
        phone_layout = QVBoxLayout()
        phone_label = QLabel("Phone Number:")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        phone_layout.addWidget(phone_label)
        phone_layout.addWidget(self.phone_input)
        form_layout.addLayout(phone_layout)
        
        # LRN
        lrn_layout = QVBoxLayout()
        lrn_label = QLabel("LRN (Learner's Reference Number):")
        self.lrn_input = QLineEdit()
        self.lrn_input.setPlaceholderText("Enter LRN")
        lrn_layout.addWidget(lrn_label)
        lrn_layout.addWidget(self.lrn_input)
        form_layout.addLayout(lrn_layout)
        
        # Grade Level
        grade_layout = QVBoxLayout()
        grade_label = QLabel("Grade Level:")
        self.grade_combo = QComboBox()
        self.grade_combo.addItems([
            "Select Grade Level",
            "Grade 11",
            "Grade 12",
            "1st Year College",
            "2nd Year College",
            "3rd Year College",
            "4th Year College"
        ])
        grade_layout.addWidget(grade_label)
        grade_layout.addWidget(self.grade_combo)
        form_layout.addLayout(grade_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.proceed_btn = QPushButton("Proceed to Detection")
        self.proceed_btn.clicked.connect(self.validate_and_proceed)
        self.proceed_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.proceed_btn)
        layout.addLayout(button_layout)
        
    def validate_and_proceed(self):
        """Validate form and proceed if valid"""
        name = self.name_input.text().strip()
        strand = self.strand_combo.currentText()
        age = self.age_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        lrn = self.lrn_input.text().strip()
        grade = self.grade_combo.currentText()
        
        # Basic validation
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter the student's name.")
            return
            
        if strand == "Select Strand":
            QMessageBox.warning(self, "Validation Error", "Please select a strand.")
            return
            
        if not age:
            QMessageBox.warning(self, "Validation Error", "Please enter the student's age.")
            return
            
        if grade == "Select Grade Level":
            QMessageBox.warning(self, "Validation Error", "Please select a grade level.")
            return
        
        # Store student info
        self.student_info = {
            'name': name,
            'strand': strand,
            'age': age,
            'email': email,
            'phone': phone,
            'lrn': lrn,
            'grade': grade
        }
        
        self.accept()
        
    def get_student_info(self):
        """Return the collected student information"""
        return getattr(self, 'student_info', None)

class ViolationLogbookDialog(QDialog):
    """Dialog for displaying and printing student violation logbook"""
    
    def __init__(self, student_info, violations, parent=None):
        super().__init__(parent)
        self.student_info = student_info
        self.violations = violations
        self.setWindowTitle("Student Violation Logbook")
        self.setModal(True)
        self.resize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0c0c17, stop:0.5 #1a1a2e, stop:1 #16213e);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: 500;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: 800;
                color: #ffffff;
                text-align: center;
                margin-bottom: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            QTextEdit {
                background: rgba(30, 30, 45, 0.8);
                color: #ffffff;
                border: 2px solid #3a3a4e;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7d2ae8, stop:1 #3a86ff);
                transform: translateY(-2px);
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin-top: 10px;
                padding: 10px;
                background: rgba(20, 20, 35, 0.6);
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #a0a0c0;
            }
        """)
        
        self.init_ui()
        self.generate_logbook()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Student Violation Logbook")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Student info section
        info_group = QGroupBox("Student Information")
        info_layout = QVBoxLayout()
        
        student_details = f"""
Name: {self.student_info.get('name', 'N/A')}
Strand: {self.student_info.get('strand', 'N/A')}
Age: {self.student_info.get('age', 'N/A')}
Grade Level: {self.student_info.get('grade', 'N/A')}
Email: {self.student_info.get('email', 'N/A')}
Phone: {self.student_info.get('phone', 'N/A')}
LRN: {self.student_info.get('lrn', 'N/A')}
"""
        info_label = QLabel(student_details.strip())
        info_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; line-height: 1.5;")
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Violations log
        violations_group = QGroupBox("Violation Records")
        violations_layout = QVBoxLayout()
        
        self.logbook_text = QTextEdit()
        self.logbook_text.setReadOnly(True)
        violations_layout.addWidget(self.logbook_text)
        violations_group.setLayout(violations_layout)
        layout.addWidget(violations_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.print_btn = QPushButton("Print Logbook")
        self.print_btn.clicked.connect(self.print_logbook)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
    def generate_logbook(self):
        """Generate the formatted violation logbook"""
        logbook_content = "=" * 80 + "\n"
        logbook_content += "                    STUDENT VIOLATION LOGBOOK\n"
        logbook_content += "=" * 80 + "\n\n"
        
        # Student header
        logbook_content += "STUDENT INFORMATION:\n"
        logbook_content += "-" * 40 + "\n"
        logbook_content += f"Name: {self.student_info.get('name', 'N/A')}\n"
        logbook_content += f"Strand: {self.student_info.get('strand', 'N/A')}\n"
        logbook_content += f"Age: {self.student_info.get('age', 'N/A')}\n"
        logbook_content += f"Grade Level: {self.student_info.get('grade', 'N/A')}\n"
        logbook_content += f"Email: {self.student_info.get('email', 'N/A')}\n"
        logbook_content += f"Phone: {self.student_info.get('phone', 'N/A')}\n"
        logbook_content += f"LRN: {self.student_info.get('lrn', 'N/A')}\n\n"
        
        # Violations section
        logbook_content += "VIOLATION RECORDS:\n"
        logbook_content += "-" * 40 + "\n"
        
        if self.violations:
            for i, violation in enumerate(self.violations, 1):
                logbook_content += f"\nVIOLATION #{i}\n"
                logbook_content += f"Date/Time: {violation.get('timestamp', 'N/A')}\n"
                logbook_content += f"Type: {violation.get('violation_type', 'N/A')}\n"
                logbook_content += f"Description: {violation.get('description', 'N/A')}\n"
                logbook_content += f"Reported By: {violation.get('reported_by', 'N/A')}\n"
                logbook_content += "-" * 30 + "\n"
        else:
            logbook_content += "\nNo violations recorded for this student.\n"
        
        logbook_content += "\n" + "=" * 80 + "\n"
        logbook_content += f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
        logbook_content += "=" * 80 + "\n"
        
        self.logbook_text.setPlainText(logbook_content)
        
    def print_logbook(self):
        """Print the violation logbook"""
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec_() == QDialog.Accepted:
                self.logbook_text.print_(printer)
                QMessageBox.information(self, "Print Success", "Logbook has been sent to printer.")
        except ImportError:
            QMessageBox.warning(self, "Print Error", "Printing functionality is not available on this system.")

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #6a11cb, stop:1 #2575fc);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                font-size: 14px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #2575fc, stop:1 #6a11cb);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #1a5cb3, stop:1 #4a0c8f);
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

def create_shadow(self, radius=20, offset=5):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(0, 0, 0, 80))
    shadow.setOffset(offset, offset)
    return shadow

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.mysql_available = MYSQL_AVAILABLE
        if self.mysql_available:
            self.connect_mysql()
        else:
            print("[INFO] Using file-based storage (violations.json)")

    def connect_mysql(self):
        """Connect to MySQL database"""
        if not self.mysql_available:
            return False

        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',  # XAMPP default empty password
                database='violation_tracker'
            )
            if self.connection.is_connected():
                print("[OK] Connected to MySQL database")
                return True
        except Error as e:
            print(f"[ERROR] MySQL connection error: {e}")
            print("[INFO] Falling back to file-based storage")

        self.mysql_available = False
        return False

    def save_violation(self, student_name, violation_type, description, reported_by=None, gender='Unknown'):
        """Save violation to database or file"""
        current_timestamp = datetime.now()

        if self.mysql_available and self.connection:
            # Save to MySQL
            try:
                cursor = self.connection.cursor()
                # Map the typed student name to a user account (so violations go to that account)
                cursor.execute("SELECT id FROM users WHERE username = %s", (student_name,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    print("[ERROR] Student username not found in users table")
                    return False

                user_id = row[0]

                # Insert using the actual schema (user_id, violation_type, description, gender, reported_by)
                try:
                    cursor.execute(
                        "INSERT INTO violations (user_id, violation_type, description, gender, reported_by) VALUES (%s, %s, %s, %s, %s)",
                        (user_id, violation_type, description, gender, reported_by or "System")
                    )
                except Error:
                    # Fallback for older schema without reported_by
                    cursor.execute(
                        "INSERT INTO violations (user_id, violation_type, description, gender) VALUES (%s, %s, %s, %s)",
                        (user_id, violation_type, description, gender)
                    )

                self.connection.commit()
                cursor.close()
                print("[OK] Violation saved to MySQL database")
                return True
            except Error as e:
                print(f"[ERROR] MySQL save error: {e}")
                self.mysql_available = False

        # Fallback to JSON file storage
        return self.save_to_file(student_name, violation_type, description, current_timestamp, gender)

    def save_to_file(self, student_name, violation_type, description, timestamp, gender='Unknown'):
        """Save violation to JSON file"""
        try:
            # Load existing violations
            if os.path.exists('violations.json'):
                with open('violations.json', 'r') as f:
                    violations = json.load(f)
            else:
                violations = []

            # Add new violation
            violation = {
                'id': len(violations) + 1,
                'student_name': student_name,
                'violation_type': violation_type,
                'description': description,
                'gender': gender,
                'timestamp': timestamp.isoformat()
            }
            violations.append(violation)

            # Save back to file
            with open('violations.json', 'w') as f:
                json.dump(violations, f, indent=2)

            print("[OK] Violation saved to file")
            return True
        except Exception as e:
            print(f"[ERROR] File save error: {e}")
            return False

    def get_violations(self, limit=10):
        """Get recent violations from database or file"""
        if self.mysql_available and self.connection:
            # Get from MySQL
            try:
                cursor = self.connection.cursor(dictionary=True)
                query = """
                    SELECT
                        v.id,
                        u.username AS student_name,
                        v.violation_type,
                        v.description,
                        v.gender,
                        v.created_at as timestamp,
                        v.reported_by
                    FROM violations v
                    JOIN users u ON u.id = v.user_id
                    ORDER BY v.created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
                violations = cursor.fetchall()
                cursor.close()
                return violations
            except Error as e:
                print(f"[ERROR] MySQL read error: {e}")
                self.mysql_available = False

        # Fallback to JSON file
        return self.get_from_file(limit)

    def get_from_file(self, limit=10):
        """Get violations from JSON file"""
        try:
            if os.path.exists('violations.json'):
                with open('violations.json', 'r') as f:
                    violations = json.load(f)
                return violations[-limit:]  # Return last N violations
            else:
                return []
        except Exception as e:
            print(f"[ERROR] File read error: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("[OK] Database connection closed")

class HairStyleAnalyzer:
    """Analyzes hair style violations based on school rules"""
    
    HAIR_VIOLATIONS = {
        'BANGS_COVERING_EYEBROWS': 'Hair Violation - Fringe/bangs covering eyebrows',
        'UNTIDY_HAIR': 'Hair Violation - Hair not combed neatly',
        'LONG_HAIR_UNTIED': 'Hair Violation - Long hair (shoulder-length+) not tied/braided',
        'HAIR_MODIFICATION': 'Hair Violation - Unauthorized hair modification detected',
        'MESSY_HAIR': 'Hair Violation - Hair appears unkempt/messy',
        'HAIR_COLOR_VIOLATION': 'Hair Violation - Hair color is not black',
        'HAIR_CUT_VIOLATION': 'Hair Violation - Hair cut violation (too long/short for boys)',
        'NECKTIE_VIOLATION': 'Uniform Violation - Necktie not properly worn',
        'UNIFORM_VIOLATION': 'Uniform Violation - Uniform not compliant'
    }
    
    def __init__(self):
        self.hair_color_baseline = None
        self.baseline_samples = []
        self.baseline_ready = False
        
    def analyze_hair(self, gray_frame, color_frame, shape, rect, gender='unknown'):
        """Analyze hair for violations. Returns list of violation types detected."""
        violations = []
        
        # Common violations for both genders
        hair_color_violation = self.check_hair_color(color_frame, shape, rect)
        if hair_color_violation:
            violations.append(self.HAIR_VIOLATIONS['HAIR_COLOR_VIOLATION'])
        
        # Only check bangs for boys - girls are allowed to have hair on forehead
        if gender.lower() == 'male' or gender.lower() == 'boy':
            bangs_violation = self.check_bangs_covering_eyebrows(gray_frame, shape)
            if bangs_violation:
                violations.append(self.HAIR_VIOLATIONS['BANGS_COVERING_EYEBROWS'])
        
        untidy = self.check_untidy_hair(gray_frame, color_frame, shape, rect)
        if untidy:
            violations.append(self.HAIR_VIOLATIONS['UNTIDY_HAIR'])
        
        # Gender-specific violations
        if gender.lower() == 'female' or gender.lower() == 'girl':
            # For girls: hair color and uniform violations
            long_untied = self.check_long_hair_untied(gray_frame, color_frame, shape, rect)
            if long_untied:
                violations.append(self.HAIR_VIOLATIONS['LONG_HAIR_UNTIED'])
                
        elif gender.lower() == 'male' or gender.lower() == 'boy':
            # For boys: hair cut, hair color, necktie, and uniform violations
            hair_cut_violation = self.check_hair_cut_violation(gray_frame, shape, rect)
            if hair_cut_violation:
                violations.append(self.HAIR_VIOLATIONS['HAIR_CUT_VIOLATION'])
                
            necktie_violation = self.check_necktie_violation(color_frame, shape, rect)
            if necktie_violation:
                violations.append(self.HAIR_VIOLATIONS['NECKTIE_VIOLATION'])
        
        # Check uniform for both genders
        uniform_violation = self.check_uniform_violation(color_frame, shape, rect)
        if uniform_violation:
            violations.append(self.HAIR_VIOLATIONS['UNIFORM_VIOLATION'])
        
        modification = self.check_hair_modification(color_frame, shape, rect)
        if modification:
            violations.append(self.HAIR_VIOLATIONS['HAIR_MODIFICATION'])
        
        return violations
    
    def check_bangs_covering_eyebrows(self, gray, shape):
        """Check if fringe/bangs are covering eyebrows - detects hair at or below eyebrow level"""
        try:
            left_eyebrow = shape[17:22]
            right_eyebrow = shape[22:27]
            
            left_eyebrow_top = int(np.min(left_eyebrow[:, 1]))
            right_eyebrow_top = int(np.min(right_eyebrow[:, 1]))
            left_eyebrow_bottom = int(np.max(left_eyebrow[:, 1]))
            right_eyebrow_bottom = int(np.max(right_eyebrow[:, 1]))
            
            eyebrow_top = min(left_eyebrow_top, right_eyebrow_top)
            eyebrow_bottom = max(left_eyebrow_bottom, right_eyebrow_bottom)
            
            left_x = int(np.min(left_eyebrow[:, 0]))
            right_x = int(np.max(right_eyebrow[:, 0]))
            
            left_eye = shape[36:42]
            right_eye = shape[42:48]
            left_eye_top = int(np.min(left_eye[:, 1]))
            right_eye_top = int(np.min(right_eye[:, 1]))
            eye_top = min(left_eye_top, right_eye_top)
            
            x_start = max(0, left_x - 10)
            x_end = min(gray.shape[1], right_x + 10)
            
            forehead_height = 60
            forehead_y_start = max(0, eyebrow_top - forehead_height)
            forehead_y_end = eyebrow_top
            
            if forehead_y_end > forehead_y_start and x_end > x_start:
                forehead_region = gray[forehead_y_start:forehead_y_end, x_start:x_end]
                if forehead_region.size > 0:
                    forehead_mean = np.mean(forehead_region)
                else:
                    forehead_mean = 150
            else:
                forehead_mean = 150
            
            eyebrow_zone_start = eyebrow_top - 10
            eyebrow_zone_end = eyebrow_bottom + 15
            eyebrow_zone = gray[max(0, eyebrow_zone_start):min(gray.shape[0], eyebrow_zone_end), x_start:x_end]
            
            if eyebrow_zone.size > 0:
                eyebrow_zone_mean = np.mean(eyebrow_zone)
                dark_threshold = min(eyebrow_zone_mean - 20, forehead_mean - 30, 80)
                dark_pixels_eyebrow = np.sum(eyebrow_zone < dark_threshold)
                dark_ratio_eyebrow = dark_pixels_eyebrow / eyebrow_zone.size
                
                if dark_ratio_eyebrow > 0.4:
                    return True
            
            below_eyebrow_start = eyebrow_bottom
            below_eyebrow_end = eye_top - 3
            
            if below_eyebrow_end > below_eyebrow_start:
                below_eyebrow_region = gray[below_eyebrow_start:below_eyebrow_end, x_start:x_end]
                
                if below_eyebrow_region.size > 0:
                    below_mean = np.mean(below_eyebrow_region)
                    below_std = np.std(below_eyebrow_region)
                    
                    dark_threshold = min(forehead_mean - 25, 90)
                    dark_pixels = np.sum(below_eyebrow_region < dark_threshold)
                    dark_ratio = dark_pixels / below_eyebrow_region.size
                    
                    if dark_ratio > 0.25:
                        return True
                    
                    if below_mean < forehead_mean - 35 and below_std > 15:
                        return True
                    
                    edges = cv2.Canny(below_eyebrow_region, 30, 100)
                    edge_density = np.sum(edges > 0) / edges.size
                    if edge_density > 0.15 and below_mean < forehead_mean - 20:
                        return True
            
            between_brows_x_start = int((left_x + right_x) / 2 - 20)
            between_brows_x_end = int((left_x + right_x) / 2 + 20)
            between_brows_y_start = eyebrow_top - 5
            between_brows_y_end = eyebrow_bottom + 10
            
            between_brows = gray[max(0, between_brows_y_start):min(gray.shape[0], between_brows_y_end),
                                 max(0, between_brows_x_start):min(gray.shape[1], between_brows_x_end)]
            
            if between_brows.size > 0:
                between_mean = np.mean(between_brows)
                if between_mean < forehead_mean - 40:
                    return True
            
            if forehead_y_end > forehead_y_start + 20:
                upper_forehead = gray[forehead_y_start:forehead_y_start + 25, x_start:x_end]
                lower_forehead = gray[forehead_y_end - 25:forehead_y_end, x_start:x_end]
                
                if upper_forehead.size > 0 and lower_forehead.size > 0:
                    upper_mean = np.mean(upper_forehead)
                    lower_mean = np.mean(lower_forehead)
                    
                    if lower_mean < upper_mean - 25:
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking bangs: {e}")
            return False
    
    def check_untidy_hair(self, gray, color_frame, shape, rect):
        """Check if hair appears unkempt/not combed neatly"""
        try:
            face_top = rect.top()
            face_left = rect.left()
            face_right = rect.right()
            
            hair_region_height = int(rect.height() * 0.4)
            y_start = max(0, face_top - hair_region_height)
            y_end = face_top
            x_start = max(0, face_left - 20)
            x_end = min(gray.shape[1], face_right + 20)
            
            if y_end <= y_start or x_end <= x_start:
                return False
            
            hair_region = gray[y_start:y_end, x_start:x_end]
            if hair_region.size == 0:
                return False
            
            edges = cv2.Canny(hair_region, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            sobelx = cv2.Sobel(hair_region, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(hair_region, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            gradient_std = np.std(gradient_magnitude)
            
            laplacian = cv2.Laplacian(hair_region, cv2.CV_64F)
            texture_variance = np.var(laplacian)
            
            if edge_density > 0.25 and gradient_std > 50 and texture_variance > 800:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking untidy hair: {e}")
            return False
    
    def check_long_hair_untied(self, gray, color_frame, shape, rect):
        """Check if long hair (shoulder-length or longer) is not tied/braided - for females"""
        try:
            face_bottom = rect.bottom()
            face_left = rect.left()
            face_right = rect.right()
            face_center_x = (face_left + face_right) // 2
            face_height = rect.height()
            
            shoulder_distance = int(face_height * 1.2)
            check_y_start = face_bottom
            check_y_end = min(gray.shape[0], face_bottom + shoulder_distance)
            
            left_region_x_start = max(0, face_left - int(face_height * 0.5))
            left_region_x_end = face_left + 20
            
            right_region_x_start = face_right - 20
            right_region_x_end = min(gray.shape[1], face_right + int(face_height * 0.5))
            
            if check_y_end <= check_y_start:
                return False
            
            hair_detected_left = False
            hair_detected_right = False
            
            if left_region_x_end > left_region_x_start:
                left_region = gray[check_y_start:check_y_end, left_region_x_start:left_region_x_end]
                if left_region.size > 0:
                    left_mean = np.mean(left_region)
                    left_std = np.std(left_region)
                    if left_mean < 100 and left_std < 40:
                        hair_detected_left = True
            
            if right_region_x_end > right_region_x_start:
                right_region = gray[check_y_start:check_y_end, right_region_x_start:right_region_x_end]
                if right_region.size > 0:
                    right_mean = np.mean(right_region)
                    right_std = np.std(right_region)
                    if right_mean < 100 and right_std < 40:
                        hair_detected_right = True
            
            neck_x_start = face_center_x - 30
            neck_x_end = face_center_x + 30
            neck_region = gray[check_y_start:check_y_end, max(0, neck_x_start):min(gray.shape[1], neck_x_end)]
            
            hair_on_back = False
            if neck_region.size > 0:
                neck_mean = np.mean(neck_region)
                if neck_mean < 90:
                    hair_on_back = True
            
            if (hair_detected_left or hair_detected_right) and hair_on_back:
                return True
            
            if hair_detected_left and hair_detected_right:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking long hair: {e}")
            return False
    
    def check_hair_modification(self, color_frame, shape, rect):
        """Check for unauthorized hair modifications (coloring, highlights, etc.)"""
        try:
            face_top = rect.top()
            face_left = rect.left()
            face_right = rect.right()
            
            hair_region_height = int(rect.height() * 0.5)
            y_start = max(0, face_top - hair_region_height)
            y_end = face_top + 10
            x_start = max(0, face_left - 30)
            x_end = min(color_frame.shape[1], face_right + 30)
            
            if y_end <= y_start or x_end <= x_start:
                return False
            
            hair_region = color_frame[y_start:y_end, x_start:x_end]
            if hair_region.size == 0:
                return False
            
            hsv_region = cv2.cvtColor(hair_region, cv2.COLOR_BGR2HSV)
            
            h_channel = hsv_region[:, :, 0]
            s_channel = hsv_region[:, :, 1]
            v_channel = hsv_region[:, :, 2]
            
            red_mask1 = (h_channel < 10) & (s_channel > 100)
            red_mask2 = (h_channel > 170) & (s_channel > 100)
            red_pixels = np.sum(red_mask1 | red_mask2)
            
            blonde_mask = (h_channel > 15) & (h_channel < 35) & (s_channel > 80) & (v_channel > 150)
            blonde_pixels = np.sum(blonde_mask)
            
            blue_mask = (h_channel > 100) & (h_channel < 130) & (s_channel > 100)
            blue_pixels = np.sum(blue_mask)
            
            green_mask = (h_channel > 35) & (h_channel < 85) & (s_channel > 100)
            green_pixels = np.sum(green_mask)
            
            purple_mask = (h_channel > 130) & (h_channel < 160) & (s_channel > 100)
            purple_pixels = np.sum(purple_mask)
            
            total_pixels = hair_region.shape[0] * hair_region.shape[1]
            unnatural_color_ratio = (red_pixels + blue_pixels + green_pixels + purple_pixels) / total_pixels
            blonde_ratio = blonde_pixels / total_pixels
            
            if unnatural_color_ratio > 0.15:
                return True
            
            if blonde_ratio > 0.3:
                return True
            
            h_std = np.std(h_channel)
            if h_std > 40:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking hair modification: {e}")
            return False
    
    def check_hair_color(self, color_frame, shape, rect):
        """Check if hair color is not black"""
        try:
            face_top = rect.top()
            face_left = rect.left()
            face_right = rect.right()
            
            hair_region_height = int(rect.height() * 0.4)
            y_start = max(0, face_top - hair_region_height)
            y_end = face_top
            x_start = max(0, face_left - 20)
            x_end = min(color_frame.shape[1], face_right + 20)
            
            if y_end <= y_start or x_end <= x_start:
                return False
            
            hair_region = color_frame[y_start:y_end, x_start:x_end]
            if hair_region.size == 0:
                return False
            
            hsv_region = cv2.cvtColor(hair_region, cv2.COLOR_BGR2HSV)
            h_channel = hsv_region[:, :, 0]
            s_channel = hsv_region[:, :, 1]
            v_channel = hsv_region[:, :, 2]
            
            # Check for non-black colors
            # Black hair typically has low saturation and medium brightness
            # Non-black colors have higher saturation or different hue ranges
            
            # Check for blonde/light hair
            blonde_mask = ((h_channel > 15) & (h_channel < 60) & (s_channel > 30) & (v_channel > 120))
            blonde_pixels = np.sum(blonde_mask)
            
            # Check for red hair
            red_mask1 = (h_channel < 10) & (s_channel > 50)
            red_mask2 = (h_channel > 170) & (s_channel > 50)
            red_pixels = np.sum(red_mask1 | red_mask2)
            
            # Check for other unnatural colors
            blue_mask = (h_channel > 90) & (h_channel < 130) & (s_channel > 50)
            blue_pixels = np.sum(blue_mask)
            
            green_mask = (h_channel > 35) & (h_channel < 85) & (s_channel > 50)
            green_pixels = np.sum(green_mask)
            
            purple_mask = (h_channel > 130) & (h_channel < 160) & (s_channel > 50)
            purple_pixels = np.sum(purple_mask)
            
            total_pixels = hair_region.shape[0] * hair_region.shape[1]
            non_black_ratio = (blonde_pixels + red_pixels + blue_pixels + green_pixels + purple_pixels) / total_pixels
            
            # If more than 20% of hair is non-black, it's a violation
            if non_black_ratio > 0.2:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking hair color: {e}")
            return False
    
    def check_hair_cut_violation(self, gray_frame, shape, rect):
        """Check hair cut violation for boys (hair too long or too short)"""
        try:
            face_top = rect.top()
            face_height = rect.height()
            
            # Get forehead region to check hair length
            forehead_y_start = max(0, face_top - int(face_height * 0.3))
            forehead_y_end = face_top
            forehead_x_start = rect.left()
            forehead_x_end = rect.right()
            
            if forehead_y_end > forehead_y_start:
                forehead_region = gray_frame[forehead_y_start:forehead_y_end, forehead_x_start:forehead_x_end]
                if forehead_region.size > 0:
                    forehead_mean = np.mean(forehead_region)
                    
                    # Check if hair is covering too much forehead (too long)
                    # or if forehead is too visible (too short - shaved/bald)
                    
                    # For boys, hair should not be too long (covering eyebrows)
                    # and not too short (military cut is usually acceptable)
                    
                    # This is a simplified check - in practice, you'd need more sophisticated analysis
                    # For now, we'll flag if hair seems excessively long
                    if forehead_mean < 100:  # Dark hair covering forehead
                        return True
                    
            return False
            
        except Exception as e:
            print(f"Error checking hair cut: {e}")
            return False
    
    def check_necktie_violation(self, color_frame, shape, rect):
        """Check if necktie is properly worn"""
        try:
            face_bottom = rect.bottom()
            face_left = rect.left()
            face_right = rect.right()
            face_height = rect.height()
            
            # Check neck region for necktie
            neck_y_start = face_bottom
            neck_y_end = min(color_frame.shape[0], face_bottom + int(face_height * 0.8))
            neck_x_start = max(0, face_left - int(face_height * 0.2))
            neck_x_end = min(color_frame.shape[1], face_right + int(face_height * 0.2))
            
            if neck_y_end > neck_y_start:
                neck_region = color_frame[neck_y_start:neck_y_end, neck_x_start:neck_x_end]
                if neck_region.size > 0:
                    # Convert to HSV for color analysis
                    hsv_neck = cv2.cvtColor(neck_region, cv2.COLOR_BGR2HSV)
                    
                    # Look for red/blue necktie colors (typical school necktie colors)
                    # This is a simplified check
                    h_channel = hsv_neck[:, :, 0]
                    s_channel = hsv_neck[:, :, 1]
                    
                    # Red necktie detection
                    red_mask = ((h_channel < 10) | (h_channel > 170)) & (s_channel > 50)
                    red_pixels = np.sum(red_mask)
                    
                    # Blue necktie detection
                    blue_mask = (h_channel > 90) & (h_channel < 130) & (s_channel > 50)
                    blue_pixels = np.sum(blue_mask)
                    
                    total_pixels = neck_region.shape[0] * neck_region.shape[1]
                    necktie_pixels = red_pixels + blue_pixels
                    
                    # If less than 5% of neck region has necktie colors, assume no necktie
                    if necktie_pixels / total_pixels < 0.05:
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking necktie: {e}")
            return False
    
    def check_uniform_violation(self, color_frame, shape, rect):
        """Check if uniform is compliant"""
        try:
            face_bottom = rect.bottom()
            face_left = rect.left()
            face_right = rect.right()
            face_height = rect.height()
            
            # Check torso region for uniform
            torso_y_start = face_bottom
            torso_y_end = min(color_frame.shape[0], face_bottom + int(face_height * 1.5))
            torso_x_start = max(0, face_left - int(face_height * 0.3))
            torso_x_end = min(color_frame.shape[1], face_right + int(face_height * 0.3))
            
            if torso_y_end > torso_y_start:
                torso_region = color_frame[torso_y_start:torso_y_end, torso_x_start:torso_x_end]
                if torso_region.size > 0:
                    # Convert to HSV for color analysis
                    hsv_torso = cv2.cvtColor(torso_region, cv2.COLOR_BGR2HSV)
                    
                    # Look for typical uniform colors (white, light blue, etc.)
                    # This is a simplified check - in practice, you'd compare against known uniform colors
                    h_channel = hsv_torso[:, :, 0]
                    s_channel = hsv_torso[:, :, 1]
                    v_channel = hsv_torso[:, :, 2]
                    
                    # Check for very bright or very dark clothing (non-uniform)
                    bright_pixels = np.sum(v_channel > 200)
                    dark_pixels = np.sum(v_channel < 50)
                    
                    total_pixels = torso_region.shape[0] * torso_region.shape[1]
                    
                    # If too much bright or dark clothing, might be non-uniform
                    if (bright_pixels + dark_pixels) / total_pixels > 0.6:
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error checking uniform: {e}")
            return False


class FaceDetector(QThread):
    update_frame_signal = pyqtSignal(np.ndarray, list, bool, list)
    violation_detected = pyqtSignal(str, str)
    
    def __init__(self, camera_index=0):
        super().__init__()
        self.running = True
        self.camera_index = camera_index
        try:
            dlib_module = get_dlib()
            if dlib_module:
                self.detector = dlib_module.get_frontal_face_detector()
                self.predictor = dlib_module.shape_predictor("shape_predictor_68_face_landmarks.dat")
                self.face_detection_enabled = True
            else:
                self.face_detection_enabled = False
                print("[WARNING] Face detection disabled - dlib not available")
        except Exception as e:
            self.face_detection_enabled = False
            print(f"[WARNING] Face detection disabled: {e}")
        
        self.hair_analyzer = HairStyleAnalyzer()
        self.last_violation_time = {}
        self.violation_cooldown = 10
        self.last_face_detection = 0
        self.face_detection_interval = 5
        self.frame_count = 0
        self.detection_interval = 3
        self.low_light_mode = True
    
    def enhance_low_light(self, frame):
        """Enhance image for better detection in low-light conditions"""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        alpha = 1.3
        beta = 20
        enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
        
        enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)
        
        return enhanced
    
    def enhance_gray_for_detection(self, gray):
        """Enhance grayscale image for better face detection"""
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        enhanced = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
        
        return enhanced
    
    def is_low_light(self, frame):
        """Check if frame is in low-light condition"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        return mean_brightness < 80
    
    def is_backlit(self, frame):
        """Check if frame has backlighting (bright background, dark foreground)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        center_region = gray[h//4:3*h//4, w//4:3*w//4]
        edge_top = gray[0:h//6, :]
        edge_bottom = gray[5*h//6:, :]
        edge_left = gray[:, 0:w//6]
        edge_right = gray[:, 5*w//6:]
        
        center_brightness = np.mean(center_region)
        edge_brightness = np.mean([np.mean(edge_top), np.mean(edge_bottom), 
                                   np.mean(edge_left), np.mean(edge_right)])
        
        contrast = np.std(gray)
        
        return (edge_brightness - center_brightness > 40) or (contrast > 70 and edge_brightness > 150)
    
    def enhance_backlit(self, frame):
        """Enhance backlit images by balancing exposure"""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        l_enhanced = cv2.normalize(l_enhanced, None, 30, 220, cv2.NORM_MINMAX)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v = cv2.add(v, 30)
        v = np.clip(v, 0, 255).astype(np.uint8)
        hsv_enhanced = cv2.merge([h, s, v])
        enhanced = cv2.cvtColor(hsv_enhanced, cv2.COLOR_HSV2BGR)
        
        gamma = 0.7
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
        enhanced = cv2.LUT(enhanced, table)
        
        return enhanced
    
    def enhance_gray_backlit(self, gray):
        """Enhanced grayscale processing for backlit conditions"""
        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        
        enhanced = cv2.normalize(enhanced, None, 0, 255, cv2.NORM_MINMAX)
        
        gamma = 0.6
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
        enhanced = cv2.LUT(enhanced, table)
        
        enhanced = cv2.bilateralFilter(enhanced, 5, 50, 50)
        
        return enhanced
    
    def set_camera(self, camera_index):
        self.camera_index = camera_index
          
    def run(self):
        """Run the face detection loop"""
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"Error: Could not open camera {self.camera_index}.")
                return
            
            if not self.face_detection_enabled:
                print("[INFO] Face detection disabled - showing video feed only")
                
            while self.running:
                try:
                    ret, frame = cap.read()
                    if not ret:
                        continue
                        
                    frame = imutils.resize(frame, width=640)
                    self.frame_count += 1
                    
                    display_frame = frame.copy()
                    is_dark = self.is_low_light(frame)
                    is_backlit = self.is_backlit(frame)
                    
                    if is_backlit:
                        display_frame = self.enhance_backlit(frame)
                    elif is_dark and self.low_light_mode:
                        display_frame = self.enhance_low_light(frame)
                    
                    violation_detected = False
                    rects_list = []
                    current_violations = []
                    
                    if self.face_detection_enabled and self.frame_count % self.detection_interval == 0:
                        if is_backlit:
                            enhanced_frame = self.enhance_backlit(frame)
                            gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
                            gray = self.enhance_gray_backlit(gray)
                        elif is_dark:
                            enhanced_frame = self.enhance_low_light(frame)
                            gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
                            gray = self.enhance_gray_for_detection(gray)
                        else:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            gray = self.enhance_gray_for_detection(gray)
                        
                        rects = self.detector(gray, 0)
                        
                        if len(rects) == 0:
                            if is_backlit:
                                gray_boosted = cv2.convertScaleAbs(gray, alpha=1.8, beta=50)
                                gray_boosted = cv2.equalizeHist(gray_boosted)
                                rects = self.detector(gray_boosted, 0)
                                if len(rects) == 0:
                                    rects = self.detector(gray_boosted, 1)
                            elif is_dark:
                                gray_boosted = cv2.convertScaleAbs(gray, alpha=1.5, beta=30)
                                gray_boosted = cv2.equalizeHist(gray_boosted)
                                rects = self.detector(gray_boosted, 0)
                  
                        for rect in rects:
                            try:
                                shape = self.predictor(gray, rect)
                                shape = face_utils.shape_to_np(shape)
                                
                                violations = self.hair_analyzer.analyze_hair(gray, frame, shape, rect, 'unknown')
                                
                                current_time = time.time()
                                for violation in violations:
                                    last_time = self.last_violation_time.get(violation, 0)
                                    if (current_time - last_time) > self.violation_cooldown:
                                        violation_detected = True
                                        self.last_violation_time[violation] = current_time
                                        self.violation_detected.emit("Unknown Student", violation)
                                        current_violations.append(violation)
                                        
                                        if (current_time - self.last_face_detection) > self.face_detection_interval:
                                            self.last_face_detection = current_time
                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                            violation_type_short = violation.split(' - ')[1][:20].replace(' ', '_')
                                            filename = f"detected_faces/violation_{violation_type_short}_{timestamp}.jpg"
                                            os.makedirs(os.path.dirname(filename), exist_ok=True)
                                            cv2.imwrite(filename, display_frame)
                                
                                for i, (x, y) in enumerate(shape):
                                    if i in range(17, 27):
                                        cv2.circle(display_frame, (x, y), 2, (0, 255, 255), -1)
                                    elif i in range(36, 48):
                                        cv2.circle(display_frame, (x, y), 2, (0, 255, 0), -1)
                                
                            except Exception as e:
                                print(f"Error processing face: {str(e)}")
                                continue
                        
                        rects_list = [(r.left(), r.top(), r.width(), r.height()) for r in rects]
                    
                    if is_backlit:
                        cv2.putText(display_frame, "BACKLIGHT MODE", (10, 25), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    elif is_dark:
                        cv2.putText(display_frame, "LOW LIGHT MODE", (10, 25), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    if self.receivers(self.update_frame_signal) > 0:
                        self.update_frame_signal.emit(display_frame, rects_list, violation_detected, current_violations)
                    
                except Exception as e:
                    print(f"Error in face detection loop: {str(e)}")
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"Fatal error in face detector thread: {str(e)}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
    
    def stop(self):
        self.running = False
        if self.isRunning():
            self.wait(1000)
            if self.isRunning():
                self.terminate()


class ViolationTracker(QMainWindow):
    def __init__(self, user_id, username, student_info=None):
        super().__init__()
        self.user_id = user_id
        self.username = username
        self.student_info = student_info or {}
        
        # If no student info provided, show the student info dialog first
        if not self.student_info:
            self.show_student_info_dialog()
            return
        
        # Continue with normal initialization if student info is available
        self.initialize_main_window()
    
    def show_student_info_dialog(self):
        """Show student information dialog as the first step"""
        dialog = StudentInfoDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.student_info = dialog.get_student_info()
            # Now initialize the main window with student info
            self.initialize_main_window()
        else:
            # User cancelled, close the application
            self.close()
    
    def initialize_main_window(self):
        """Initialize the main window after student info is collected"""
        self.setWindowTitle(f"VIOLATION TRACKER - {self.student_info.get('name', 'Unknown Student')}")
        self.setGeometry(50, 50, 1600, 950)
        
        # Set up the main window with dark 3D theme
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0c0c17, stop:0.5 #1a1a2e, stop:1 #16213e);
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: 500;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: rgba(30, 30, 45, 0.8);
                color: #ffffff;
                border: 2px solid #3a3a4e;
                border-radius: 8px;
                padding: 12px 18px;
                font-size: 14px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                min-height: 24px;
                selection-background-color: #4a4a6a;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #6a11cb;
                box-shadow: 0 0 0 2px rgba(106, 17, 203, 0.3);
            }
            QFrame#mainFrame {
                background: rgba(30, 30, 45, 0.85);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
            }
            QLabel#titleLabel {
                font-size: 32px;
                font-weight: 800;
                color: #ffffff;
                padding: 25px 0;
                text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
                letter-spacing: 2px;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a11cb, stop:1 #2575fc);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                box-shadow: 0 4px 15px rgba(37, 117, 252, 0.3);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7d2ae8, stop:1 #3a86ff);
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(37, 117, 252, 0.4);
            }
            QPushButton:pressed {
                transform: translateY(1px);
                box-shadow: 0 2px 10px rgba(37, 117, 252, 0.3);
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                margin-top: 15px;
                padding: 15px;
                background: rgba(20, 20, 35, 0.6);
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #a0a0c0;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(30, 30, 45, 0.8);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #6a11cb;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: url(dropdown_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)

        # Initialize components
        self.db_manager = DatabaseManager()
        self.violations = []
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.camera_active = False
        self.current_camera_index = 0
        
        # Initialize face detector
        self.face_detector = FaceDetector(self.current_camera_index)
        self.face_detector.update_frame_signal.connect(self.update_frame)
        self.face_detector.violation_detected.connect(self.auto_log_violation)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize the user interface"""
        # Create main widget with 3D perspective
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Add shadow effect to main widget
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        main_widget.setGraphicsEffect(shadow)
        
        # Main layout with 3D perspective
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(30)

        # Left panel - Camera with 3D effect
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setObjectName("mainFrame")
        
        # Add 3D effect to left panel
        left_shadow = QGraphicsDropShadowEffect()
        left_shadow.setBlurRadius(30)
        left_shadow.setColor(QColor(0, 0, 0, 150))
        left_shadow.setOffset(5, 10)
        left_panel.setGraphicsEffect(left_shadow)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(20)

        # Camera label
        self.camera_label = QLabel("Camera is off")
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            background: #f8f9fa;
            border: 2px dashed #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            color: #666;
        """)
        left_layout.addWidget(self.camera_label)

        # Camera selection
        camera_select_layout = QHBoxLayout()
        camera_select_label = QLabel("Select Camera:")
        camera_select_label.setStyleSheet("color: white; font-weight: bold;")
        self.camera_combo = QComboBox()
        self.camera_combo.setStyleSheet("""
            QComboBox {
                color: white;
                background-color: #2a2a3e;
                border: 1px solid #6a11cb;
                padding: 8px;
                border-radius: 6px;
                min-width: 200px;
            }
            QComboBox QAbstractItemView {
                color: white;
                background-color: #2a2a3e;
                selection-background-color: #6a11cb;
                selection-color: white;
            }
        """)
        self.detect_cameras()
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        camera_select_layout.addWidget(camera_select_label)
        camera_select_layout.addWidget(self.camera_combo)
        camera_select_layout.addStretch()
        
        refresh_cam_btn = QPushButton("Refresh")
        refresh_cam_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-size: 12px;
            }
        """)
        refresh_cam_btn.clicked.connect(self.detect_cameras)
        camera_select_layout.addWidget(refresh_cam_btn)
        left_layout.addLayout(camera_select_layout)

        # Camera controls
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Camera")
        self.start_btn.clicked.connect(self.toggle_camera)
        controls_layout.addWidget(self.start_btn)
        left_layout.addLayout(controls_layout)
        
        # Status label
        self.status_label = QLabel("Camera off")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-weight: bold;
            color: black;
            padding: 8px;
            border-radius: 5px;
            background: #f44336;
        """)
        left_layout.addWidget(self.status_label)

        # Create right panel for form and violations list
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_panel.setObjectName("mainFrame")
        
        # Add 3D effect to right panel
        right_shadow = QGraphicsDropShadowEffect()
        right_shadow.setBlurRadius(30)
        right_shadow.setColor(QColor(0, 0, 0, 150))
        right_shadow.setOffset(5, 10)
        right_panel.setGraphicsEffect(right_shadow)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(25, 25, 25, 25)
        right_layout.setSpacing(20)

        # Form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        # Form title
        form_title = QLabel("Report Violation")
        form_title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 600;
                color: #e0e0e0;
                margin-bottom: 10px;
                padding-bottom: 8px;
                border-bottom: 2px solid #6a11cb;
            }
        """)
        form_layout.addWidget(form_title)

        # Student name
        name_label = QLabel("Student Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter student name")
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)

        # Gender
        gender_label = QLabel("Gender:")
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Unknown", "Male", "Female"])
        self.gender_combo.setCurrentText("Unknown")
        form_layout.addWidget(gender_label)
        form_layout.addWidget(self.gender_combo)

        # Violation type
        type_label = QLabel("Violation Type:")
        type_label.setStyleSheet("color: white;")
        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("""
            QComboBox {
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView {
                color: white;
                background-color: white;
                selection-background-color: #4CAF50;
                selection-color: white;
            }
        """)
        self.type_combo.addItems(["Hair Violation", "Uniform Violation", "Tardiness", "Disrespect", "Other"])
        form_layout.addWidget(type_label)
        form_layout.addWidget(self.type_combo)


        # Description
        desc_label = QLabel("Description:")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Enter violation details...")
        self.desc_input.setMaximumHeight(100)
        form_layout.addWidget(desc_label)
        form_layout.addWidget(self.desc_input)

        # Log violation button
        self.log_btn = QPushButton("Log Violation")
        self.log_btn.clicked.connect(self.log_violation)
        form_layout.addWidget(self.log_btn)
        
        # View logbook button
        self.logbook_btn = QPushButton("View Violation Logbook")
        self.logbook_btn.clicked.connect(self.show_logbook)
        self.logbook_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6b35, stop:1 #f7931e);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff8c42, stop:1 #ffb347);
                transform: translateY(-2px);
            }
        """)
        form_layout.addWidget(self.logbook_btn)
        form_layout.addStretch()
        
        # Add form to right layout
        right_layout.addLayout(form_layout)

        # Violations list with 3D card effect
        violations_header = QLabel("Recent Violations")
        violations_header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 600;
                color: #e0e0e0;
                margin: 20px 0 15px 0;
                padding-bottom: 8px;
                border-bottom: 2px solid #6a11cb;
            }
        """)
        right_layout.addWidget(violations_header)
        
        # Create a scroll area for violations
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container widget for scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(15)
        
        # Violation list as a scrollable area
        self.violation_list_layout = QVBoxLayout()
        scroll_layout.addLayout(self.violation_list_layout)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        right_layout.addWidget(scroll)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        right_layout.addWidget(scroll, 1)  # The '1' makes it stretchable

        # Add panels to main layout
        main_layout.addWidget(left_panel, 60)
        main_layout.addWidget(right_panel, 40)

        # Add user info label at the top
        user_info = QLabel(f"Logged in as: {self.username}")
        user_info.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background: rgba(106, 17, 203, 0.3);
                border-radius: 5px;
                margin: 5px;
            }
        """)
        
        # Add logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedWidth(100)
        logout_btn.clicked.connect(self.logout)
        
        # Create a horizontal layout for user info and logout button
        user_bar = QHBoxLayout()
        user_bar.addWidget(user_info)
        user_bar.addStretch()
        user_bar.addWidget(logout_btn)
        
        # Main content layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.addLayout(user_bar)
        
        # Add the main content to the central widget
        main_layout.addWidget(content_widget)
        self.setCentralWidget(main_widget)
        
        # Add shadow effect to main widget
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        main_widget.setGraphicsEffect(shadow)

    def auto_log_violation(self, student_name, violation_type):
        """Automatically log a violation when detected by face detection"""
        # Use student name from form if available
        actual_student_name = self.student_info.get('name', student_name) if self.student_info else student_name
        
        if self.db_manager.save_violation(actual_student_name, violation_type, "Automatically detected by system", self.username):
            self.load_data()  # Refresh violations list
            # Show a brief notification
            self.status_label.setText(f"{violation_type} detected!")
            QTimer.singleShot(3000, lambda: self.status_label.setText("Camera on - Ready") if self.camera_active else None)

    def toggle_camera(self):
        """Toggle camera on/off"""
        if not self.camera_active:
            self.start_btn.setText("Stop Camera")
            self.camera_active = True
            
            # Start face detection in a separate thread
            if not self.face_detector.isRunning():
                self.face_detector.start()
                
            self.status_label.setText("Camera on - Ready")
            self.status_label.setStyleSheet(
                "font-weight: bold;"
                "color: black;"
                "padding: 8px;"
                "border-radius: 5px;"
                "background: #4CAF50;"
            )
        else:
            # Stop face detection thread
            if self.face_detector.isRunning():
                self.face_detector.stop()
                
            self.camera_active = False
            self.start_btn.setText("Start Camera")
            self.camera_label.clear()
            self.camera_label.setText("Camera is off")
            self.status_label.setText("Camera off")
            self.status_label.setStyleSheet(
                "font-weight: bold;"
                "color: white;"
                "padding: 8px;"
                "border-radius: 5px;"
                "background: #f44336;"
            )

    def detect_cameras(self):
        """Detect available cameras on the system"""
        self.camera_combo.clear()
        available_cameras = []
        
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        
        if available_cameras:
            for cam_index in available_cameras:
                self.camera_combo.addItem(f"Camera {cam_index}", cam_index)
        else:
            self.camera_combo.addItem("No camera found", -1)
        
        if self.current_camera_index in available_cameras:
            index = available_cameras.index(self.current_camera_index)
            self.camera_combo.setCurrentIndex(index)

    def change_camera(self, index):
        """Change to a different camera"""
        if index < 0:
            return
            
        camera_index = self.camera_combo.currentData()
        if camera_index is None or camera_index < 0:
            return
            
        if camera_index == self.current_camera_index:
            return
        
        was_active = self.camera_active
        
        if self.camera_active:
            if self.face_detector.isRunning():
                self.face_detector.stop()
            self.camera_active = False
        
        self.current_camera_index = camera_index
        
        self.face_detector = FaceDetector(self.current_camera_index)
        self.face_detector.update_frame_signal.connect(self.update_frame)
        self.face_detector.violation_detected.connect(self.auto_log_violation)
        
        if was_active:
            self.face_detector.start()
            self.camera_active = True
            self.status_label.setText(f"Camera {camera_index} - Ready")
        else:
            self.camera_label.setText(f"Camera {camera_index} selected - Click Start")

    def update_frame(self, frame=None, face_rects=None, violation_detected=False, violations=None):
        """Update the camera frame with face detection results"""
        if frame is None:
            return

        if violations is None:
            violations = []

        if face_rects is not None:
            for (x, y, w, h) in face_rects:
                color = (0, 0, 255) if violation_detected else (0, 255, 0)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                if violation_detected and violations:
                    label = "VIOLATION DETECTED"
                    bg_color = (0, 0, 255)
                else:
                    label = "FACE DETECTED"
                    bg_color = (0, 200, 0)
                
                text_color = (255, 255, 255)
                
                (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                
                cv2.rectangle(frame, 
                            (x, y - 25), 
                            (x + text_width + 10, y), 
                            bg_color, -1)
                
                cv2.putText(frame, label, 
                          (x + 5, y - 7), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
                
                if violation_detected and violations:
                    y_offset = y + h + 20
                    for i, v in enumerate(violations[:3]):
                        violation_text = v.split(' - ')[1] if ' - ' in v else v
                        violation_text = violation_text[:35] + "..." if len(violation_text) > 35 else violation_text
                        
                        (vw, vh), _ = cv2.getTextSize(violation_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(frame, (x, y_offset - 15), (x + vw + 10, y_offset + 5), (0, 0, 180), -1)
                        cv2.putText(frame, violation_text, (x + 5, y_offset), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        y_offset += 25

        # Convert to QImage
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Display the image
        self.camera_label.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.camera_label.width(),
            self.camera_label.height(),
            Qt.KeepAspectRatio
        ))

    def log_violation(self):
        """Log a violation to the database"""
        student_name = self.name_input.text().strip()
        violation_type = self.type_combo.currentText()
        description = self.desc_input.toPlainText().strip()
        gender = self.gender_combo.currentText()

        if not student_name:
            QMessageBox.warning(self, "Error", "Please enter a student name.")
            return

        if not description:
            QMessageBox.warning(self, "Error", "Please enter a description.")
            return

        # Save to database
        if self.db_manager.save_violation(student_name, violation_type, description, self.username, gender):
            # Clear form
            self.name_input.clear()
            self.desc_input.clear()
            self.gender_combo.setCurrentText("Unknown")

            # Refresh violations list
            self.load_data()

            QMessageBox.information(self, "Success",
                                 f"Violation logged successfully!\n\n"
                                 f"Student: {student_name}\n"
                                 f"Type: {violation_type}\n"
                                 f"Gender: {gender}\n"
                                 f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            QMessageBox.critical(self, "Error", "Failed to save violation to database.")

    def show_logbook(self):
        """Show the violation logbook for the current student"""
        if not self.student_info:
            QMessageBox.warning(self, "No Student Info", "No student information available. Please restart the application.")
            return
        
        # Get violations for this student
        student_name = self.student_info.get('name', '')
        if not student_name:
            QMessageBox.warning(self, "No Student Name", "Student name is not available.")
            return
        
        # Get all violations for this student
        violations = self.db_manager.get_violations_by_student(student_name)
        
        # Show logbook dialog
        logbook_dialog = ViolationLogbookDialog(self.student_info, violations, self)
        logbook_dialog.exec_()

    def load_data(self):
        """Load recent violations from database"""
        violations = self.db_manager.get_violations(10)
        self.update_violation_list(violations)

    def update_violation_list(self, violations):
        """Update the violations list display"""
        # Clear existing items
        for i in reversed(range(self.violation_list_layout.count())):
            self.violation_list_layout.itemAt(i).widget().setParent(None)
        
        # Add violations to the list
        for violation in violations:
            # Create violation item widget
            item = QFrame()
            item.setStyleSheet("""
                QFrame {
                    background: rgba(40, 40, 60, 0.8);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                    border-left: 4px solid #6a11cb;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QLabel#violationType {
                    color: #ff6b6b;
                    font-weight: bold;
                    font-size: 15px;
                }
                QLabel#studentName {
                    font-weight: bold;
                    font-size: 16px;
                    color: #ffffff;
                }
            """)
            
            layout = QVBoxLayout(item)
            
            # Student name and violation type
            header = QHBoxLayout()
            name_label = QLabel(violation.get('student_name', 'Unknown'))
            name_label.setObjectName("studentName")
            type_label = QLabel(violation.get('violation_type', 'Unknown'))
            type_label.setObjectName("violationType")
            
            header.addWidget(name_label)
            header.addStretch()
            header.addWidget(type_label)
            
            # Description
            desc_label = QLabel(violation.get('description', 'No description'))
            desc_label.setWordWrap(True)
            
            # Timestamp
            timestamp = violation.get('timestamp', '')
            if isinstance(timestamp, str):
                try:
                    # Try to parse the timestamp string
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    timestamp = dt.strftime('%b %d, %Y %I:%M %p')
                except:
                    pass
            
            time_label = QLabel(timestamp)
            time_label.setStyleSheet("color: #a0a0c0; font-size: 12px;")
            
            # Reported by
            reported_by = QLabel(f"Reported by: {violation.get('reported_by', 'System')}")
            reported_by.setStyleSheet("color: #a0a0c0; font-size: 12px;")
            
            # Add widgets to layout
            layout.addLayout(header)
            layout.addWidget(desc_label)
            
            footer = QHBoxLayout()
            footer.addWidget(time_label)
            footer.addStretch()
            footer.addWidget(reported_by)
            
            layout.addLayout(footer)
            
            # Add to the list
            self.violation_list_layout.addWidget(item)
    
    def logout(self):
        # Close the current window and show login window
        self.close()
        QApplication.instance().logout()

class MainApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.auth_window = None
        self.main_window = None
        self.show_login()
    
    def show_login(self):
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        self.auth_window = LoginWindow()
        self.auth_window.login_success.connect(self.on_login_success)
        try:
            screen = self.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                x = geo.x() + max(0, (geo.width() - self.auth_window.width()) // 2)
                y = geo.y() + max(0, (geo.height() - self.auth_window.height()) // 2)
                self.auth_window.move(x, y)
        except Exception:
            pass
        self.auth_window.show()
        try:
            self.auth_window.showNormal()
            self.auth_window.raise_()
            self.auth_window.activateWindow()
        except Exception:
            pass
    
    def on_login_success(self, user_id, username):
        if self.auth_window:
            self.auth_window.close()
            self.auth_window = None
        
        # Create ViolationTracker - it will handle student info collection internally
        self.main_window = ViolationTracker(user_id, username)
            
        try:
            screen = self.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                x = geo.x() + max(0, (geo.width() - self.main_window.width()) // 2)
                y = geo.y() + max(0, (geo.height() - self.main_window.height()) // 2)
                self.main_window.move(x, y)
        except Exception:
            pass
        self.main_window.show()
        try:
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception:
            pass
    
    def logout(self):
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        self.show_login()

def main():
    app = MainApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Start the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
