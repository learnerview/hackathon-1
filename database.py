import sqlite3

def create_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Create the 'users' table (no change from the original)
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'pdf_data' table to store the extracted text from uploaded PDFs
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS pdf_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the 'pdf_responses' table to store the response and match percentage
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS pdf_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            response_text TEXT NOT NULL,
            match_percentage REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_db()
