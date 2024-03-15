from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import date
from werkzeug.utils import secure_filename
import os
import tensorflow as tf
from PIL import Image
import numpy as np
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///malaria_management.db' 
app.secret_key = 'secret123'
db = SQLAlchemy(app)

# SQLite database configuration
DATABASE_NAME = 'malaria_management.db'

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Check if the provided username and password are valid
def is_valid_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve the user from the database based on the provided username
    cursor.execute('SELECT * FROM Users WHERE LOWER(Username) = LOWER(?)', (username,))
    user = cursor.fetchone()

    # Check if the user exists and the password is correct
    if user and user['Password'] == password.strip():
        return True
    else:
        return False

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load the TensorFlow model
MODEL_PATH = 'models/my_model.h5'  
model = tf.keras.models.load_model(MODEL_PATH)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html', result=None)  # Pass 'result' as None initially

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Preprocess the image for the model
        img = Image.open(filepath)
        img = img.resize((50, 50))  
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # Make predictions
        predictions = model.predict(img_array)
        result = 'Infected' if predictions[0][0] > 0.5 else 'Uninfected'

        # Remove the uploaded file
        os.remove(filepath)

        return render_template('addpatient.html', result=result)  # Pass 'result' to the template

    return jsonify({'error': 'Invalid file format'})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if is_valid_user(username, password):
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Corrected route name
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard(): 
    # Connect to the SQLite database
    conn = sqlite3.connect('malaria_management.db')
    cursor = conn.cursor()
    cursor1 = conn.cursor()

    # Retrieve patient records from the database
    cursor.execute("SELECT COUNT(*) FROM patients")
    p_count = cursor.fetchone()[0]

    # Retrieve doctors records from the database
    cursor1.execute("SELECT COUNT(*) FROM Doctors")
    d_count = cursor1.fetchone()[0]


    # Close the database connection
    conn.close()
    return render_template('dashboard.html',p_count=p_count,d_count=d_count)

@app.route('/patient')
def patient():
    # Logic to render the patient page goes here
    # Connect to the SQLite database
    conn = sqlite3.connect('malaria_management.db')
    cursor = conn.cursor()

    # Retrieve patient records from the database
    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Render the HTML template and pass the patient records 
    return render_template('patient.html',patients=patients)

@app.route('/addpatient', methods=['GET', 'POST'])
def addpatient():
    if request.method == 'POST':
        # Get form data
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        insurance = request.form.get('insurance')
        phone = request.form.get('phone')
        result = request.form.get('result')
        
        # Get a database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute the insert query
        cursor.execute("INSERT INTO patients (fname, lname, insurance, phone, result) VALUES (?, ?, ?, ?, ?)",
                       (fname, lname, insurance, phone, result))
        
        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        flash('Patient added successfully!', 'success') 
    
    return render_template('addpatient.html') 

@app.route('/doctor')
def doctor():
    # Logic to render the doctor page goes here
    # Connect to the SQLite database
    conn = sqlite3.connect('malaria_management.db')
    cursor = conn.cursor()

    # Retrieve patient records from the database
    cursor.execute("SELECT * FROM Doctors")
    doctors = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Render the HTML template and pass the patient records 
    return render_template('doctor.html',doctors=doctors) 

@app.route('/adddoctor', methods=['GET', 'POST'])
def adddoctor():
    if request.method == 'POST':
        # Get form data
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        insurance = request.form.get('insurance')
        phone = request.form.get('phone') 
        
        # Get a database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute the insert query
        cursor.execute("INSERT INTO Doctors (fname, lname, insurance, phone) VALUES (?, ?, ?, ?)",
                       (fname, lname, insurance, phone))
        
        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        flash('Doctor added successfully!', 'success') 
    
    return render_template('adddoctor.html') 

@app.route('/delete/<int:patient_id>', methods=['POST', 'GET'])
def delete_patient(patient_id):
    # Get a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the SQL delete statement with parameterized query
    cursor.execute("DELETE FROM patients WHERE patientid = ?", (patient_id,))
    conn.commit()

    # Close the database connection
    conn.close()

    # Flash a success message
    flash('Patient deleted successfully!', 'success')

    # Redirect to the patient page
    return redirect(url_for('patient'))

@app.route('/delete/<int:doctors_id>', methods=['POST'])
def delete_doctor(doctors_id):
    # Get a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the SQL delete statement with parameterized query
    cursor.execute("DELETE FROM Doctors WHERE DoctorID = ?", (doctors_id,))
    conn.commit()

    # Close the database connection
    conn.close()

    # Flash a success message
    flash('Doctor deleted successfully!', 'success')

    # Redirect to the doctor page
    return redirect(url_for('doctor'))
    

if __name__ == '__main__':
    app.run(debug=True)
