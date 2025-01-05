from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import bcrypt
import os
from PIL import Image
import fitz
import google.generativeai as genai
import io
import base64
import markdown
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Google API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyDlq0H5zsbxNpAdDKwqIzPiOZuuEUcix_s"))
app.secret_key = os.getenv("SECRET_KEY", "AIzaSyDlq0H5zsbxNpAdDKwqIzPiOZuuEUcix_s")


# Database connection function
def connect_db():
    return sqlite3.connect('users.db')

# Function to process uploaded PDF and extract text
def extract_pdf_text(uploaded_file):
    try:
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None

# Function to process Gemini API response
def get_gemini_response(input_text, pdf_content, prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
                {"role": "user", "content": f"Job Description: {input_text}"},
                {"role": "user", "content": f"Resume Content: {pdf_content}"}
            ]
        )
        return response.generations[0].message['content']
    except Exception as e:
        print(f"Error in Gemini API: {str(e)}")
        return f"Error in generating response: {str(e)}"

# Prompt mapping
PROMPTS = {
    "analyze_resume": """Conduct a detailed analysis of the resume against the job description, highlighting strengths, weaknesses, and alignment with the role.
    Respond in Markdown format:
    - **Overview**
    - **Strengths**
    - **Weaknesses**
    - **Final Verdict**""",

    "percentage_match": """Calculate the alignment percentage between the resume and the job description. Respond in Markdown:
    - **Match Percentage**
    - **Matched Keywords**
    - **Missing Keywords**
    - **Suggestions**"""
}

# Home route for login page
@app.route('/')
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# Registration page route
@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

# Route to handle registration form submission
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(''' 
            INSERT INTO users (username, email, password_hash) 
            VALUES (?, ?, ?)
        ''', (username, email, hashed_password))
        conn.commit()
        conn.close()
        return redirect(url_for('login_page'))
    except sqlite3.IntegrityError:
        conn.close()
        return "Error: Username or email already exists", 400

# Route to handle login form submission
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(''' 
        SELECT password_hash FROM users WHERE username = ?
    ''', (username,))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[0]):
        session['username'] = username
        conn.close()
        return redirect(url_for('home'))
    else:
        conn.close()
        return "Invalid username or password", 400

# Route for home page
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'username' not in session:
        return redirect(url_for('login_page'))

    response = None
    error = None
    pdf_data = []

    if request.method == "POST":
        input_text = request.form.get("job_description")
        uploaded_files = request.files.getlist("resume_files")
        task = request.form.get("task")

        input_prompt = PROMPTS.get(task)
        if not input_prompt:
            error = "Invalid task selected."
        elif uploaded_files:
            for uploaded_file in uploaded_files:
                pdf_text = extract_pdf_text(uploaded_file)
                if pdf_text:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute(''' 
                        INSERT INTO pdf_data (file_name, extracted_text) 
                        VALUES (?, ?)
                    ''', (uploaded_file.filename, pdf_text))
                    conn.commit()

                    gemini_response = get_gemini_response(input_text, pdf_text, input_prompt)

                    match_percentage = 0
                    if task == "percentage_match":
                        job_keywords = set(input_text.split())
                        resume_keywords = set(pdf_text.split())
                        matched_keywords = job_keywords.intersection(resume_keywords)
                        total_keywords = len(job_keywords)
                        match_percentage = (len(matched_keywords) / total_keywords) * 100 if total_keywords else 0

                    cursor.execute(''' 
                        INSERT INTO pdf_responses (file_name, response_text, match_percentage) 
                        VALUES (?, ?, ?)
                    ''', (uploaded_file.filename, gemini_response, match_percentage))
                    conn.commit()
                    conn.close()

                    pdf_data.append({
                        'file_name': uploaded_file.filename,
                        'extracted_text': pdf_text,
                        'gemini_response': gemini_response,
                        'match_percentage': match_percentage
                    })
                else:
                    error = "Error processing one of the uploaded PDFs."

            if not error:
                response = markdown.markdown("Extracted Texts from multiple resumes stored successfully.")
        else:
            error = "Please upload at least one resume PDF."

    return render_template("index.html", response=response, error=error, pdf_data=pdf_data, username=session['username'])

# Route to display complete database
@app.route('/work', methods=['GET'])
def work():
    if 'username' not in session:
        return redirect(url_for('login_page'))

    conn = connect_db()
    cursor = conn.cursor()

    # Retrieve all records from database
    cursor.execute('''SELECT * FROM pdf_data''')
    pdf_data_records = cursor.fetchall()

    cursor.execute('''SELECT * FROM pdf_responses''')
    response_records = cursor.fetchall()

    conn.close()

    return render_template('work.html', pdf_data_records=pdf_data_records, response_records=response_records)

# Route to handle logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)
