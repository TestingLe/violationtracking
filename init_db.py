import mysql.connector
from mysql.connector import Error
import hashlib

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_database():
    try:
        # Connect to MySQL server (without specifying a database)
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''  # XAMPP default empty password
        )
        
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS violation_tracker")
        print("Database 'violation_tracker' created or already exists")
        
        # Use the database
        cursor.execute("USE violation_tracker")
        
        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            face_encoding LONGBLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        
        # Create an admin user (password: admin123)
        admin_password = hash_password('admin123')
        cursor.execute("""
        INSERT IGNORE INTO users (username, password) 
        VALUES (%s, %s)
        """, ('admin', admin_password))
        
        connection.commit()
        print("Database tables created successfully")
        
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed")

if __name__ == "__main__":
    create_database()
