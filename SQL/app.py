from flask import Flask, render_template, redirect, url_for, request, session
import mysql.connector
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'your_secret_key'


UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Database connection
def get_db():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="kamal2005",
        database="symptomsage"
    )
    return db

# Create tables
with app.app_context():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors
                 (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), age INT, gender VARCHAR(10), password VARCHAR(255), hospital VARCHAR(255))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS patients
                 (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), age INT, gender VARCHAR(10), password VARCHAR(255), scan_path VARCHAR(255), result VARCHAR(255), detailed_rep TEXT, prescription TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctor_patient_map
                 (id INT AUTO_INCREMENT PRIMARY KEY, doctor_id INT, patient_id INT)''')
    db.commit()
    cursor.close()
    db.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, name FROM doctors WHERE name = %s AND password = %s", (name, password))
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
        if doctor:
            session['doctor_id'] = doctor[0]
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT patient_id FROM doctor_patient_map WHERE doctor_id = %s", (doctor[0],))
            patient_ids = [p[0] for p in cursor.fetchall()]
            if patient_ids:
                placeholders = ','.join(['%s'] * len(patient_ids))
                cursor.execute(f"SELECT name FROM patients WHERE id IN ({placeholders})", tuple(patient_ids))
                patient_names = [p[0] for p in cursor.fetchall()]
                session['patient_names'] = ', '.join(patient_names)
            else:
                session['patient_names'] = ''
            cursor.close()
            db.close()
            return redirect(url_for('doctor_dashboard'))
        else:
            return render_template('doctor_login.html', error='Invalid credentials')
    return render_template('doctor_login.html')

@app.route('/doctor_signup', methods=['GET', 'POST'])
def doctor_signup():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        password = request.form['password']
        hospital = request.form['Hospital']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO doctors (name, age, gender, password, hospital) VALUES (%s, %s, %s, %s, %s)", (name, age, gender, password,hospital))
        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('doctor_login'))
    return render_template('doctor_signup.html')

@app.route('/doctor_dashboard')
def doctor_dashboard():
    doctor_id = session['doctor_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.name, p.age, p.gender, p.scan_path, p.result, p.detailed_rep, p.prescription
        FROM patients p
        INNER JOIN doctor_patient_map dpm ON p.id = dpm.patient_id
        WHERE dpm.doctor_id = %s
        ORDER BY p.id DESC
    """, (doctor_id,))
    patients = cursor.fetchall()
    
    # Group patient reports by patient name
    patient_reports = {}
    for patient in patients:
        name = patient[0]
        if name not in patient_reports:
            patient_reports[name] = []
        patient_reports[name].append(patient)
    
    cursor.close()
    db.close()
    return render_template('doctor_dashboard.html', patient_reports=patient_reports)

@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM patients WHERE name = %s AND password = %s", (name, password))
        patient = cursor.fetchone()
        cursor.close()
        db.close()
        if patient:
            session['patient_id'] = patient[0]
            return redirect(url_for('patient_dashboard'))
        else:
            return render_template('patient_login.html', error='Invalid credentials')
    return render_template('patient_login.html')

@app.route('/patient_signup', methods=['GET', 'POST'])
def patient_signup():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO patients (name, age, gender, password) VALUES (%s, %s, %s, %s)", (name, age, gender, password))
        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('patient_login'))
    return render_template('patient_signup.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    patient_id = session.get('patient_id')
    
    if patient_id is None:
        return "Patient ID not found in session"
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Fetch patient details
        cursor.execute("""
            SELECT p.name, p.age, p.gender, p.scan_path, p.result, p.detailed_rep, p.prescription, d.name AS doctor_name, d.hospital
            FROM patients p
            LEFT JOIN doctor_patient_map dpm ON p.id = dpm.patient_id
            LEFT JOIN doctors d ON dpm.doctor_id = d.id
            WHERE p.id = %s
        """, (patient_id,))
        patient = cursor.fetchone()
        
        if patient is None:
            return "Patient not found in the database"
        
        return render_template('patient_dashboard.html', patient=patient)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
    finally:
        cursor.close()
        db.close()

@app.route('/health_tracker')
def health_tracker():
    patient_id = session['patient_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT scan_path, prescription FROM patients WHERE id = %s", (patient_id,))
    patient_data = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('health_tracker.html', patient_data=patient_data)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        result = request.form['result']
        detailed_rep = request.form['detailed_rep']
        prescription = request.form['prescription']
        doctor_id = session['doctor_id']
        db = get_db()
        cursor = db.cursor()

        # Handle file upload
        file = request.files['scan_path']
        scan_path = None  # Initialize scan_path as None
        if file and file.filename:
            # Save the file with a secure filename
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            scan_path = filename  # Store the filename in the database

        # Check if the patient already exists
        cursor.execute("SELECT id FROM patients WHERE name = %s", (name,))
        patient = cursor.fetchone()

        if patient:
            # Update the existing patient's details
            patient_id = patient[0]
            cursor.execute("UPDATE patients SET age=%s, gender=%s, scan_path=%s, result=%s, detailed_rep=%s, prescription=%s WHERE id=%s",
                           (age, gender, scan_path, result, detailed_rep, prescription, patient_id))
        else:
            # Insert a new patient
            cursor.execute("INSERT INTO patients (name, age, gender, scan_path, result, detailed_rep, prescription) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (name, age, gender, scan_path, result, detailed_rep, prescription))
            patient_id = cursor.lastrowid

        # Check if the doctor-patient mapping already exists
        cursor.execute("SELECT id FROM doctor_patient_map WHERE doctor_id = %s AND patient_id = %s", (doctor_id, patient_id))
        mapping = cursor.fetchone()

        if not mapping:
            # Insert the doctor-patient mapping
            cursor.execute("INSERT INTO doctor_patient_map (doctor_id, patient_id) VALUES (%s, %s)", (doctor_id, patient_id))

        db.commit()
        cursor.close()
        db.close()
        return redirect(url_for('doctor_dashboard'))

    return render_template('add_patient.html')
@app.route('/remove_patient', methods=['GET', 'POST'])
def remove_patient():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        doctor_id = session['doctor_id']
        db = get_db()
        cursor = db.cursor()

        # Fetch the patient ID based on the patient name
        cursor.execute("SELECT id FROM patients WHERE name = %s", (patient_name,))
        result = cursor.fetchone()

        if result:
            patient_id = result[0]

            # Remove the mapping from the doctor_patient_map table
            cursor.execute("DELETE FROM doctor_patient_map WHERE doctor_id = %s AND patient_id = %s", (doctor_id, patient_id))
            db.commit()

        cursor.close()
        db.close()
        return redirect(url_for('doctor_dashboard'))

    return render_template('remove_patient.html')

if __name__ == '__main__':
    app.run(debug=True)