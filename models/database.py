import mysql.connector
from mysql.connector import Error
from config.config import DB_CONFIG

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("Successfully connected to the database")
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
    
    def execute_query(self, query, params=None, fetch=False):
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                self.connection.commit()
                return cursor.lastrowid
        except Error as e:
            print(f"Error executing query: {e}")
            return None
    
    def get_violations_by_student(self, student_name):
        """Get all violations for a specific student"""
        query = """
            SELECT id, student_name, violation_type, description, gender, 
                   created_at as timestamp, reported_by
            FROM violations 
            WHERE student_name = %s 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (student_name,), fetch=True)

def initialize_database():
    db = DatabaseManager()
    if db.connect():
        create_tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS violations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                student_name VARCHAR(100) NOT NULL,
                violation_type VARCHAR(100) NOT NULL,
                description TEXT,
                gender VARCHAR(20) DEFAULT 'Unknown',
                reported_by VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        ]
        
        for query in create_tables:
            db.execute_query(query)
        
        # Create admin user if not exists
        db.execute_query("""
            INSERT IGNORE INTO users (username, password) 
            VALUES ('admin', 'admin123')
        """)
        
        db.close()

if __name__ == "__main__":
    initialize_database()
