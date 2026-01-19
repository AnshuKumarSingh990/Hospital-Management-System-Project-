from flask import Flask, request, redirect, url_for, render_template_string, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import re

app = Flask(__name__)

db_config = {
    'host': 'localhost',
    'user': 'root',       # change to your MySQL username
    'password': 'manager',   # change to your MySQL password
    'database': 'hospital_management'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print("Error connecting to MySQL", e)
        return None

def parse_availability(availability_str):
    day_map = {'Mon':0,'Tue':1,'Wed':2,'Thu':3,'Fri':4,'Sat':5,'Sun':6}
    try:
        parts = availability_str.split(' ')
        days_part = parts[0]
        time_part = parts[1]

        days = set()
        if '-' in days_part:
            start_day, end_day = days_part.split('-')
            start_idx = day_map.get(start_day, None)
            end_idx = day_map.get(end_day, None)
            if start_idx is not None and end_idx is not None:
                for d in range(start_idx, end_idx+1):
                    days.add(d)
        elif ',' in days_part:
            day_names = days_part.split(',')
            for dn in day_names:
                idx = day_map.get(dn, None)
                if idx is not None:
                    days.add(idx)
        else:
            idx = day_map.get(days_part, None)
            if idx is not None:
                days.add(idx)

        def parse_time(tstr):
            tstr = tstr.strip().lower()
            if 'am' in tstr or 'pm' in tstr:
                dt = datetime.strptime(tstr, '%I%p')
            else:
                try:
                    dt = datetime.strptime(tstr, '%H:%M')
                except:
                    dt = datetime.strptime(tstr, '%H')
            return dt.time()

        start_str, end_str = re.split('-|to', time_part)
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)

        return {'days': days, 'start_time': start_time, 'end_time': end_time}
    except Exception as e:
        return {'days': set(range(7)), 'start_time': datetime.strptime('09:00','%H:%M').time(), 'end_time': datetime.strptime('17:00','%H:%M').time()}

def generate_time_slots(start_time, end_time, slot_length_minutes=30):
    slots = []
    current = datetime.combine(datetime.today(), start_time)
    end = datetime.combine(datetime.today(), end_time)
    while current + timedelta(minutes=slot_length_minutes) <= end:
        slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=slot_length_minutes)
    return slots

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Hospital Management System</title>
      <!-- Font Awesome CDN for icons -->
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" 
            integrity="sha512-papbUfypG9+A5hYKz3dR+lSRqJVoD6hfAoc/XPnTXuXgyXEnL4s59fMq8UJQTq2hvFy75U9N6RFWXEqBJoYv0A==" crossorigin="anonymous" referrerpolicy="no-referrer" />
      <style>
        /* Reset & basics */
        *, *::before, *::after {
          box-sizing: border-box;
        }
        body {
          margin: 0; padding: 0;
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background: linear-gradient(135deg, #d0e2fd 30%, #eef5fb 100%);
          color: #2f3e63;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          animation: fadeIn 1s ease forwards;
        }
        @keyframes fadeIn {
          from {opacity: 0;}
          to {opacity: 1;}
        }
        .container {
          background: white;
          width: 100%;
          max-width: 960px;
          margin: 40px 20px 60px;
          border-radius: 16px;
          box-shadow: 0 12px 28px rgba(0,0,0,0.14);
          padding: 40px;
          text-align: center;
          position: relative;
        }
        header {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 24px;
          margin-bottom: 15px;
        }
        header img {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          box-shadow: 0 4px 12px rgba(41,128,185,0.35);
        }
        h1 {
          font-size: 3.2rem;
          font-weight: 900;
          color: #1a3950;
          margin: 0;
          letter-spacing: 2px;
          user-select: none;
        }
        .subtitle {
          font-weight: 500;
          color: #4a6580;
          font-size: 1.25rem;
          margin-top: -6px;
          margin-bottom: 24px;
          user-select: none;
        }
        .description {
          max-width: 680px;
          margin: 0 auto 40px;
          color: #546e8a;
          font-size: 1.1rem;
          line-height: 1.5;
        }
        nav.grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 28px;
          margin-top: 10px;
        }
        a.card {
          background: #2980b9;
          color: white;
          padding: 24px 15px;
          border-radius: 14px;
          font-weight: 700;
          text-decoration: none;
          box-shadow: 0 6px 18px rgba(41,128,185,0.5);
          transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease;
          display: flex;
          flex-direction: column;
          align-items: center;
          user-select: none;
        }
        a.card i {
          font-size: 3.6rem;
          margin-bottom: 18px;
          filter: drop-shadow(0 0 3px rgba(0,0,0,0.12));
        }
        a.card:hover, a.card:focus {
          background-color: #20609f;
          transform: translateY(-8px);
          box-shadow: 0 12px 36px rgba(41,128,185,0.75);
          outline: none;
        }
        .footer {
          color: #7a8a9f;
          font-size: 14px;
          padding: 15px 20px;
          text-align: center;
          width: 100%;
          border-top: 1px solid #dbe2ea;
          background: #f0f4f8;
          margin-top: auto;
          user-select: none;
        }
        .footer .social-icons {
          margin-top: 8px;
        }
        .footer .social-icons a {
          margin: 0 10px;
          color: #7a8a9f;
          text-decoration: none;
          font-size: 20px;
          transition: color 0.3s ease;
        }
        .footer .social-icons a:hover, .footer .social-icons a:focus {
          color: #2980b9;
          outline: none;
        }
        @media (max-width: 480px) {
          h1 {
            font-size: 2.4rem;
          }
          a.card {
            padding: 18px 12px;
          }
          a.card i {
            font-size: 3rem;
            margin-bottom: 14px;
          }
        }
      </style>
    </head>
    <body>
      <div class="container" role="main" aria-label="Hospital Management System Main Page">
        <header>
          <h1>Hospital Management System</h1>
        </header>
        <p class="subtitle">Your Health Management, Simplified</p>
        <p class="description">
          Manage patients, doctors, appointments, billing, and room availability all from this single platform. Access medical records, assign rooms, and track activity easily.
        </p>
        <nav class="grid" aria-label="Primary navigation">
          <a href="{{ url_for('register_patient') }}" class="card" aria-describedby="desc-patient" title="Register a new patient">
            <i class="fas fa-user-plus" aria-hidden="true"></i> Register Patient
          </a>
          <a href="{{ url_for('register_doctor') }}" class="card" aria-describedby="desc-doctor" title="Register a new doctor">
            <i class="fas fa-user-md" aria-hidden="true"></i> Register Doctor
          </a>
          <a href="{{ url_for('book_appointment') }}" class="card" aria-describedby="desc-appointment" title="Book an appointment">
            <i class="fas fa-calendar-check" aria-hidden="true"></i> Book Appointment
          </a>
          <a href="{{ url_for('billing') }}" class="card" aria-describedby="desc-billing" title="View billing information">
            <i class="fas fa-file-invoice-dollar" aria-hidden="true"></i> Billing
          </a>
          <a href="{{ url_for('room_availability') }}" class="card" aria-describedby="desc-room" title="Check room availability">
            <i class="fas fa-procedures" aria-hidden="true"></i> Room Availability
          </a>
          <a href="{{ url_for('patient_medical_records_list') }}" class="card" aria-describedby="desc-records" title="View patient medical records">
            <i class="fas fa-notes-medical" aria-hidden="true"></i> Patient Medical Records
          </a>
          <a href="{{ url_for('dashboard') }}" class="card" aria-describedby="desc-dashboard" title="View dashboard summary">
            <i class="fas fa-chart-line" aria-hidden="true"></i> Dashboard
          </a>
        </nav>
      </div>
      <footer class="footer" role="contentinfo">
        &copy; 2025 Hospital Management System
        <div class="social-icons" aria-label="Social media links">
          <a href="#" aria-label="Facebook" title="Follow us on Facebook" tabindex="0"><i class="fab fa-facebook-f"></i></a>
          <a href="#" aria-label="Twitter" title="Follow us on Twitter" tabindex="0"><i class="fab fa-twitter"></i></a>
          <a href="#" aria-label="LinkedIn" title="Follow us on LinkedIn" tabindex="0"><i class="fab fa-linkedin-in"></i></a>
          <a href="#" aria-label="Instagram" title="Follow us on Instagram" tabindex="0"><i class="fab fa-instagram"></i></a>
        </div>
      </footer>
    </body>
    </html>
    """)



@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    total_patients = 0
    total_doctors = 0
    upcoming_appointments = []
    available_rooms_count = 0
    recent_billings = []

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Total patients
            cursor.execute("SELECT COUNT(*) AS count FROM patients")
            total_patients = cursor.fetchone()['count']

            # Total doctors
            cursor.execute("SELECT COUNT(*) AS count FROM doctors")
            total_doctors = cursor.fetchone()['count']

            # Upcoming 5 appointments (future dates, sorted)
            today = datetime.today().strftime('%Y-%m-%d')
            now_time = datetime.now().strftime('%H:%M:%S')
            cursor.execute("""
                SELECT a.id, p.name as patient_name, d.name as doctor_name, a.date, a.time, a.room_no
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE (a.date > %s) OR (a.date = %s AND a.time >= %s)
                ORDER BY a.date, a.time
                LIMIT 5
            """, (today, today, now_time))
            upcoming_appointments = cursor.fetchall()

            # Count available rooms (rooms which are not booked today or later at any time)
            cursor.execute("""
                SELECT COUNT(*) AS count FROM rooms r
                WHERE r.room_no NOT IN (
                    SELECT room_no FROM appointments WHERE date >= CURDATE() AND room_no IS NOT NULL
                )
            """)
            available_rooms_count = cursor.fetchone()['count']

            # Recent 5 billing activities - paid appointments ordered by payment date desc (assuming billing_paid changed date is present; if not use appointment date)
            cursor.execute("""
                SELECT a.id, p.name as patient_name, d.name as doctor_name, a.date, a.time, a.billing_paid
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE a.billing_paid = TRUE
                ORDER BY a.date DESC, a.time DESC
                LIMIT 5
            """)
            recent_billings = cursor.fetchall()

            cursor.close()
        except Exception as e:
            # handle/log exception as needed
            pass
        finally:
            conn.close()

    return render_template_string(dashboard_template,
                                  total_patients=total_patients,
                                  total_doctors=total_doctors,
                                  upcoming_appointments=upcoming_appointments,
                                  available_rooms_count=available_rooms_count,
                                  recent_billings=recent_billings)

dashboard_template = """
<html>
<head>
  <title>Dashboard - Hospital Management System</title>
  <style>
    body{font-family: Arial, sans-serif; background: #f0f2f5; margin:0; padding:20px;}
    .container{max-width:900px; margin: auto; background:white; padding:25px; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
    h1, h2 { text-align:center; color:#2980b9;}
    .stats {display: flex; justify-content: space-around; margin-bottom: 30px;}
    .stat-box {background:#3498db; color:white; padding: 20px; border-radius: 8px; width: 30%; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.2);}
    table {width: 100%; border-collapse: collapse; margin-top: 15px;}
    th, td {border: 1px solid #ccc; padding: 8px; text-align: center;}
    th {background-color: #2980b9; color: white;}
    caption {caption-side: top; text-align: left; font-weight: bold; margin-bottom: 8px; font-size: 18px;}
    .no-data {color:#666; font-style: italic;}
    a {display: block; margin-top: 30px; text-align: center; color: #3498db; text-decoration:none;}
  </style>
</head>
<body>
  <div class="container">
    <h1>Dashboard</h1>
    <div class="stats">
      <div class="stat-box">
        <h2>{{ total_patients }}</h2>
        <div>Total Patients</div>
      </div>
      <div class="stat-box">
        <h2>{{ total_doctors }}</h2>
        <div>Total Doctors</div>
      </div>
      <div class="stat-box">
        <h2>{{ available_rooms_count }}</h2>
        <div>Available Rooms</div>
      </div>
    </div>

    <table>
      <caption>Upcoming Appointments (Next 5)</caption>
      <thead>
        <tr>
          <th>Appointment ID</th><th>Patient</th><th>Doctor</th><th>Date</th><th>Time</th><th>Room</th>
        </tr>
      </thead>
      <tbody>
        {% if upcoming_appointments %}
          {% for appt in upcoming_appointments %}
          <tr>
            <td>{{ appt.id }}</td>
            <td>{{ appt.patient_name }}</td>
            <td>{{ appt.doctor_name }}</td>
            <td>{{ appt.date.strftime("%Y-%m-%d") if appt.date else appt.date }}</td>
            <td>{{ appt.time }}</td>
            <td>{{ appt.room_no if appt.room_no else 'N/A' }}</td>
          </tr>
          {% endfor %}
        {% else %}
          <tr><td colspan="6" class="no-data">No upcoming appointments.</td></tr>
        {% endif %}
      </tbody>
    </table>

    <table>
      <caption>Recent Billing Activity (Last 5)</caption>
      <thead>
        <tr>
          <th>Appointment ID</th><th>Patient</th><th>Doctor</th><th>Date</th><th>Time</th><th>Status</th>
        </tr>
      </thead>
      <tbody>
        {% if recent_billings %}
          {% for bill in recent_billings %}
          <tr>
            <td>{{ bill.id }}</td>
            <td>{{ bill.patient_name }}</td>
            <td>{{ bill.doctor_name }}</td>
            <td>{{ bill.date.strftime("%Y-%m-%d") if bill.date else bill.date }}</td>
            <td>{{ bill.time }}</td>
            <td>{% if bill.billing_paid %}Paid{% else %}Unpaid{% endif %}</td>
          </tr>
          {% endfor %}
        {% else %}
          <tr><td colspan="6" class="no-data">No recent billing activity.</td></tr>
        {% endif %}
      </tbody>
    </table>

    <a href="{{ url_for('index') }}">&larr; Back to Home</a>
  </div>
</body>
</html>
"""


@app.route('/register_patient', methods=['GET', 'POST'])
def register_patient():
    msg = ""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        contact = request.form.get('contact', '').strip()
        if name and age.isdigit() and gender and contact:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO patients (name, age, gender, contact) VALUES (%s, %s, %s, %s)",
                                   (name, int(age), gender, contact))
                    conn.commit()
                    patient_id = cursor.lastrowid
                    msg = f"Patient registered successfully with ID #{patient_id}."
                except Error as e:
                    msg = "Database error: " + str(e)
                finally:
                    cursor.close()
                    conn.close()
            else:
                msg = "Failed to connect to database."
        else:
            msg = "Please fill all fields correctly."
    return render_template_string(register_patient_template, msg=msg)


register_patient_template = """
<html>
<head>
<title>Register Patient</title>
<style>
  body{font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding:0;}
  .container{max-width: 600px; margin: 40px auto; background: white; padding: 25px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
  h2{text-align:center; color:#27ae60;}
  form{display:flex; flex-direction: column;}
  label{margin: 10px 0 5px;}
  input, select{padding:10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px;}
  button{margin-top: 20px; padding:12px; background-color: #27ae60; color: white; font-weight: bold; border:none;
    border-radius: 5px; cursor: pointer;}
  button:hover{background-color: #219150;}
  .message {margin: 15px 0; font-weight: bold; color: #e74c3c;}
  a {display: inline-block; margin-top: 15px; text-decoration: none; color: #3498db;}
</style>
</head>
<body>
<div class="container">
<h2>Patient Registration</h2>
<form method="post">
  <label>Name:</label>
  <input type="text" name="name" required>
  <label>Age:</label>
  <input type="number" name="age" min="0" required>
  <label>Gender:</label>
  <select name="gender" required>
    <option value="">Select</option>
    <option>Male</option>
    <option>Female</option>
    <option>Other</option>
  </select>
  <label>Contact Number:</label>
  <input type="text" name="contact" required>
  <button type="submit">Register</button>
</form>
{% if msg %}
  <div class="message">{{msg}}</div>
{% endif %}
<a href="{{ url_for('index') }}">&larr; Back to Home</a>
</div>
</body>
</html>
"""

@app.route('/register_doctor', methods=['GET', 'POST'])
def register_doctor():
    msg = ""
    specialties = ['Cardiology', 'Dermatology', 'Neurology', 'Orthopedics', 'Pediatrics', 'General Medicine']
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        specialty = request.form.get('specialty', '')
        availability = request.form.get('availability', '').strip()
        contact = request.form.get('contact', '').strip()
        if name and specialty in specialties and availability and contact:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO doctors (name, specialty, availability, contact) VALUES (%s, %s, %s, %s)",
                        (name, specialty, availability, contact))
                    conn.commit()
                    doctor_id = cursor.lastrowid
                    msg = f"Doctor registered successfully with ID #{doctor_id}."
                except Error as e:
                    msg = "Database error: " + str(e)
                finally:
                    cursor.close()
                    conn.close()
            else:
                msg = "Failed to connect to database."
        else:
            msg = "Please fill all fields correctly."
    return render_template_string(register_doctor_template, msg=msg, specialties=specialties)

register_doctor_template = """
<html>
<head>
<title>Register Doctor</title>
<style>
  body{font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding:0;}
  .container{max-width: 600px; margin: 40px auto; background: white; padding: 25px; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
  h2{text-align:center; color:#2980b9;}
  form{display:flex; flex-direction: column;}
  label{margin: 10px 0 5px;}
  input, select{padding:10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px;}
  button{margin-top: 20px; padding:12px; background-color: #2980b9; color: white; font-weight: bold; border:none;
    border-radius: 5px; cursor: pointer;}
  button:hover{background-color: #206d9a;}
  .message {margin: 15px 0; font-weight: bold; color: #e74c3c;}
  a {display: inline-block; margin-top: 15px; text-decoration: none; color: #3498db;}
</style>
</head>
<body>
<div class="container">
<h2>Doctor Registration</h2>
<form method="post">
  <label>Name:</label>
  <input type="text" name="name" required>
  <label>Specialty:</label>
  <select name="specialty" required>
    <option value="">Select Specialty</option>
    {% for sp in specialties %}
    <option value="{{sp}}">{{sp}}</option>
    {% endfor %}
  </select>
  <label>Availability (e.g. Mon-Fri 9am-5pm):</label>
  <input type="text" name="availability" required>
  <label>Contact Number:</label>
  <input type="text" name="contact" required>
  <button type="submit">Register</button>
</form>
{% if msg %}
  <div class="message">{{msg}}</div>
{% endif %}
<a href="{{ url_for('index') }}">&larr; Back to Home</a>
</div>
</body>
</html>
"""

@app.route('/available_slots')
def available_slots():
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')

    if not doctor_id or not date_str:
        return jsonify({'error': 'Missing doctor_id or date parameter'}), 400

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to database.'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT availability FROM doctors WHERE id = %s", (doctor_id,))
        res = cursor.fetchone()
        if not res:
            return jsonify({'error': 'Doctor not found.'}), 404
        availability_str = res['availability']

        avail = parse_availability(availability_str)
        weekday = date_obj.weekday()
        if weekday not in avail['days']:
            return jsonify({'available_slots': []})

        all_slots = generate_time_slots(avail['start_time'], avail['end_time'])

        cursor.execute("SELECT time FROM appointments WHERE doctor_id = %s AND date = %s", (doctor_id, date_str))
        booked_times = [row['time'].strftime('%H:%M') for row in cursor.fetchall()]

        free_slots = [slot for slot in all_slots if slot not in booked_times]
        cursor.close()
        return jsonify({'available_slots': free_slots})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/available_rooms')
def available_rooms():
    date_str = request.args.get('date')
    time_str = request.args.get('time')

    if not date_str or not time_str:
        return jsonify({'error': 'Missing date or time parameter'}), 400

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        datetime.strptime(time_str, '%H:%M')
    except:
        return jsonify({'error': 'Invalid date or time format'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Failed to connect to database.'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT room_no FROM rooms
            WHERE room_no NOT IN (
                SELECT room_no FROM appointments WHERE date = %s AND time = %s AND room_no IS NOT NULL
            )
            ORDER BY room_no
        """, (date_str, time_str))
        available_rooms = [row['room_no'] for row in cursor.fetchall()]
        cursor.close()
        return jsonify({'available_rooms': available_rooms})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    msg = ""
    selected_specialty = request.args.get('specialty', '')
    conn = get_db_connection()
    doctors_list = []
    patients_list = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM patients ORDER BY id")
            patients_list = cursor.fetchall()
            if selected_specialty:
                cursor.execute("SELECT * FROM doctors WHERE specialty = %s", (selected_specialty,))
                doctors_list = cursor.fetchall()
            else:
                cursor.execute("SELECT DISTINCT specialty FROM doctors")
                specialties = [row['specialty'] for row in cursor.fetchall()]
            cursor.close()
        except Error as e:
            msg = "Database error: " + str(e)
        finally:
            conn.close()
    else:
        msg = "Failed to connect to database."

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', '')
        specialty = request.form.get('specialty', '')
        doctor_id = request.form.get('doctor_id', '')
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        room_no = request.form.get('room_no', '')
        try:
            patient_id_int = int(patient_id)
            doctor_id_int = int(doctor_id)
        except:
            patient_id_int = None
            doctor_id_int = None

        if patient_id_int and doctor_id_int and specialty and date and time and room_no:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE doctor_id=%s AND date=%s AND time=%s",
                                   (doctor_id_int, date, time))
                    conflict = cursor.fetchone()['cnt']
                    if conflict > 0:
                        msg = "Doctor is not available at selected date/time."
                    else:
                        cursor.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE room_no=%s AND date=%s AND time=%s",
                                       (room_no, date, time))
                        room_conflict = cursor.fetchone()['cnt']
                        if room_conflict > 0:
                            msg = "Selected room is not available at this date/time."
                        else:
                            cursor.execute("""
                                INSERT INTO appointments (patient_id, doctor_id, date, time, billing_paid, room_no)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """, (patient_id_int, doctor_id_int, date, time, False, room_no))
                            conn.commit()

                            cursor.execute("SELECT name FROM doctors WHERE id = %s", (doctor_id_int,))
                            doctor_name = cursor.fetchone()['name']
                            cursor.execute("SELECT name FROM patients WHERE id = %s", (patient_id_int,))
                            patient_name = cursor.fetchone()['name']
                            msg = (f"Appointment booked successfully with Dr. {doctor_name} "
                                   f"for patient {patient_name} on {date} at {time} in {room_no}.")
                    cursor.close()
                except Error as e:
                    msg = "Database error: " + str(e)
                finally:
                    conn.close()
            else:
                msg = "Failed to connect to database."
        else:
            msg = "Please fill all fields correctly."

    conn = get_db_connection()
    specialties = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT specialty FROM doctors")
            specialties = [row[0] for row in cursor.fetchall()]
            cursor.close()
        except Error as e:
            msg = "Database error: " + str(e)
        finally:
            conn.close()

    return render_template_string(book_appointment_template,
                                  patients_list=patients_list,
                                  doctors_list=doctors_list,
                                  specialties=specialties,
                                  selected_specialty=selected_specialty,
                                  msg=msg)

book_appointment_template = """
<html>
<head>
  <title>Book Appointment</title>
  <style>
    body{font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding:0;}
    .container{max-width: 750px; margin: 40px auto; background: white; padding: 25px; border-radius: 8px;
               box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
    h2{text-align:center; color:#8e44ad;}
    form{display:flex; flex-direction: column;}
    label{margin: 10px 0 5px;}
    select, input{padding:10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px;}
    button{margin-top: 20px; padding:12px; background-color: #8e44ad; color: white; font-weight: bold; border:none; border-radius: 5px; cursor: pointer;}
    button:hover{background-color: #71368a;}
    .message {margin: 15px 0; font-weight: bold; color: #e74c3c;}
    a {display: inline-block; margin-top: 15px; text-decoration: none; color: #3498db;}
  </style>
  <script>
    async function loadDoctors() {
      const specialty = document.getElementById('specialty').value;
      window.location = '?specialty=' + encodeURIComponent(specialty);
    }

    async function loadAvailableSlots() {
      const doctorId = document.getElementById('doctor_id').value;
      const date = document.getElementById('date').value;
      const timeSelect = document.getElementById('time');
      timeSelect.innerHTML = '<option value="">Loading...</option>';
      clearRoomOptions();
      if (!doctorId || !date) {
        timeSelect.innerHTML = '<option value="">Select doctor and date first</option>';
        return;
      }
      try {
        const response = await fetch(`/available_slots?doctor_id=${doctorId}&date=${date}`);
        const data = await response.json();
        timeSelect.innerHTML = '';
        if (data.available_slots && data.available_slots.length > 0) {
          data.available_slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot;
            option.textContent = slot;
            timeSelect.appendChild(option);
          });
        } else {
          const option = document.createElement('option');
          option.value = '';
          option.textContent = 'No available slots';
          timeSelect.appendChild(option);
        }
      } catch (error) {
        timeSelect.innerHTML = '<option value="">Error loading slots</option>';
      }
    }

    async function loadAvailableRooms() {
      const date = document.getElementById('date').value;
      const time = document.getElementById('time').value;
      const roomSelect = document.getElementById('room_no');
      roomSelect.innerHTML = '<option value="">Loading...</option>';
      if (!date || !time) {
        roomSelect.innerHTML = '<option value="">Select date and time first</option>';
        return;
      }
      try {
        const response = await fetch(`/available_rooms?date=${date}&time=${time}`);
        const data = await response.json();
        roomSelect.innerHTML = '';
        if (data.available_rooms && data.available_rooms.length > 0) {
          data.available_rooms.forEach(room => {
            const option = document.createElement('option');
            option.value = room;
            option.textContent = room;
            roomSelect.appendChild(option);
          });
        } else {
          const option = document.createElement('option');
          option.value = '';
          option.textContent = 'No rooms available';
          roomSelect.appendChild(option);
        }
      } catch (error) {
        roomSelect.innerHTML = '<option value="">Error loading rooms</option>';
      }
    }

    function clearRoomOptions() {
      const roomSelect = document.getElementById('room_no');
      roomSelect.innerHTML = '<option value="">Select date and time first</option>';
    }
  </script>
</head>
<body>
  <div class="container">
    <h2>Book Appointment</h2>
    <form method="post">
      <label>Select Patient:</label>
      <select name="patient_id" required>
        <option value="">Select Patient</option>
        {% for p in patients_list %}
        <option value="{{p.id}}">{{p.name}} (ID: {{p.id}})</option>
        {% endfor %}
      </select>

      <label>Select Specialty:</label>
      <select name="specialty" id="specialty" onchange="loadDoctors()" required>
        <option value="">Select Specialty</option>
        {% for sp in specialties %}
          <option value="{{sp}}" {% if sp == selected_specialty %}selected{% endif %}>{{sp}}</option>
        {% endfor %}
      </select>

      {% if selected_specialty %}
      <label>Select Doctor:</label>
      <select name="doctor_id" id="doctor_id" onchange="loadAvailableSlots(); clearRoomOptions();" required>
        <option value="">Select Doctor</option>
        {% for d in doctors_list %}
          <option value="{{d.id}}">{{d.name}} (Available: {{d.availability}})</option>
        {% endfor %}
      </select>

      <label>Select Date:</label>
      <input type="date" name="date" id="date" onchange="loadAvailableSlots(); clearRoomOptions();" required>

      <label>Select Time Slot:</label>
      <select name="time" id="time" onchange="loadAvailableRooms()" required>
        <option value="">Select doctor and date first</option>
      </select>

      <label>Select Room:</label>
      <select name="room_no" id="room_no" required>
        <option value="">Select date and time first</option>
      </select>
      {% endif %}
      <button type="submit">Book Appointment</button>
    </form>
    {% if msg %}
      <div class="message">{{msg}}</div>
    {% endif %}
    <a href="{{ url_for('index') }}">&larr; Back to Home</a>
  </div>
</body>
</html>
"""

@app.route('/billing', methods=['GET', 'POST'])
def billing():
    msg = ""
    if request.method == 'POST':
        appointment_id = request.form.get('appointment_id', '')
        try:
            aid = int(appointment_id)
        except:
            aid = None
        if aid:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE appointments SET billing_paid = TRUE WHERE id = %s", (aid,))
                    conn.commit()
                    msg = f"Billing paid successfully for appointment ID #{aid}."
                    cursor.close()
                except Error as e:
                    msg = "Database error: " + str(e)
                finally:
                    conn.close()
            else:
                msg = "Failed to connect to database."

    billing_data = []
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id as appointment_id, p.name as patient_name, d.name as doctor_name,
                       d.specialty, a.date, a.time, a.billing_paid, a.room_no
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                ORDER BY a.date DESC, a.time DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                row['amount'] = 100
            billing_data = rows
            cursor.close()
        except Error as e:
            msg = "Database error: " + str(e)
        finally:
            conn.close()
    else:
        msg = "Failed to connect to database."

    return render_template_string("""
    <html>
    <head>
      <title>Billing</title>
      <style>
        body{font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding:0;}
        .container{max-width: 900px; margin: 40px auto; background: white; padding: 25px; border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
        h2{text-align:center; color:#c0392b;}
        table {width: 100%; border-collapse: collapse; margin-top: 20px;}
        th, td {border: 1px solid #ccc; padding: 8px; text-align: center;}
        th {background-color: #e74c3c; color: white;}
        button {background-color: #c0392b; color: white; border: none; padding: 6px 12px; border-radius: 5px; cursor: pointer;}
        button:hover {background-color: #992d22;}
        .paid {color: green; font-weight: bold;}
        .message {margin: 15px 0; font-weight: bold; color: #27ae60; text-align:center;}
        a {display: block; margin-top: 15px; text-align: center; text-decoration: none; color: #3498db;}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Billing - Appointment Payments</h2>
        {% if billing_data %}
        <table>
          <tr>
            <th>Appointment ID</th>
            <th>Patient</th>
            <th>Doctor (Specialty)</th>
            <th>Date</th>
            <th>Time</th>
            <th>Room</th>
            <th>Amount (USD)</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
          {% for row in billing_data %}
          <tr>
            <td>{{row.appointment_id}}</td>
            <td>{{row.patient_name}}</td>
            <td>{{row.doctor_name}} ({{row.specialty}})</td>
            <td>{{row.date}}</td>
            <td>{{row.time}}</td>
            <td>{{row.room_no if row.room_no else 'N/A'}}</td>
            <td>${{row.amount}}</td>
            <td>{% if row.billing_paid %}<span class="paid">Paid</span>{% else %}Unpaid{% endif %}</td>
            <td>
              {% if not row.billing_paid %}
              <form method="post" style="margin:0;">
                <input type="hidden" name="appointment_id" value="{{row.appointment_id}}">
                <button type="submit">Pay</button>
              </form>
              {% else %}
              -
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </table>
        {% else %}
          <p>No appointments found.</p>
        {% endif %}
        {% if msg %}
          <div class="message">{{msg}}</div>
        {% endif %}
        <a href="{{ url_for('index') }}">&larr; Back to Home</a>
      </div>
    </body>
    </html>
    """, billing_data=billing_data, msg=msg)

@app.route('/room_availability')
def room_availability():
    rooms_list = []
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT room_no FROM rooms ORDER BY room_no")
            rooms_list = cursor.fetchall()
            for room in rooms_list:
                cursor.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE room_no=%s AND date >= CURDATE()", (room['room_no'],))
                count = cursor.fetchone()['cnt']
                room['occupied'] = count > 0
            cursor.close()
        except Error as e:
            rooms_list = []
        finally:
            conn.close()
    return render_template_string("""
    <html>
    <head>
      <title>Room Availability</title>
      <style>
        body{font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding:0;}
        .container{max-width: 600px; margin: 40px auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
        h2{text-align:center; color:#16a085;}
        ul {list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;}
        li {flex: 0 0 120px; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 18px; color: white;}
        .available{background-color: #27ae60;}
        .occupied{background-color: #c0392b;}
        a {display: block; margin-top: 30px; text-align: center; text-decoration: none; color: #3498db;}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Room Availability</h2>
        <ul>
          {% for room in rooms_list %}
            <li class="{{ 'occupied' if room.occupied else 'available' }}">
              {{room.room_no}}<br>
              {{ 'Occupied' if room.occupied else 'Available' }}
            </li>
          {% else %}
            <li>No room data found</li>
          {% endfor %}
        </ul>
        <a href="{{ url_for('index') }}">&larr; Back to Home</a>
      </div>
    </body>
    </html>
    """, rooms_list=rooms_list)

### New routes for medical records and prescriptions:

@app.route('/patient_medical_records')
def patient_medical_records_list():
    # Show list of patients to select to view/add medical records
    msg = request.args.get('msg','')
    conn = get_db_connection()
    patients = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM patients ORDER BY name")
            patients = cursor.fetchall()
            cursor.close()
        except:
            pass
        finally:
            conn.close()
    return render_template_string(patient_medical_records_list_template, patients=patients, msg=msg)

patient_medical_records_list_template = """
<html>
<head>
  <title>Patients - Medical Records</title>
  <style>
    body{font-family: Arial, sans-serif;background:#f0f2f5;margin:0;padding:20px;}
    .container{max-width:700px;margin:20px auto;background:white;padding:20px;border-radius:8px;
      box-shadow:0 2px 8px rgba(0,0,0,0.15);}
    h2{text-align:center;color:#27ae60;}
    ul {list-style:none; padding:0;}
    li {padding: 10px 0; border-bottom:1px solid #ccc;}
    a {color:#2980b9; text-decoration:none;}
    a:hover {text-decoration:underline;}
    .message {color:red; font-weight:bold; margin-bottom:15px; text-align:center;}
    a.home {display:block; margin-top:20px; text-align:center;}
  </style>
</head>
<body>
  <div class="container">
    <h2>Patients - Medical Records</h2>
    {% if msg %}
      <div class="message">{{ msg }}</div>
    {% endif %}
    <ul>
      {% for p in patients %}
        <li><a href="{{ url_for('view_medical_records', patient_id=p.id) }}">{{ p.name }}</a></li>
      {% endfor %}
      {% if patients|length == 0 %}
        <li>No patients found.</li>
      {% endif %}
    </ul>
    <a href="{{ url_for('index') }}" class="home">&larr; Back to Home</a>
  </div>
</body>
</html>
"""

@app.route('/patient/<int:patient_id>/medical_records', methods=['GET', 'POST'])
def view_medical_records(patient_id):
    msg = ""
    conn = get_db_connection()
    patient = None
    records = []
    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()
        doctor_id = request.form.get('doctor_id', '')
        if date and description and doctor_id:
            try:
                doc_id_int = int(doctor_id)
                dt = datetime.strptime(date, '%Y-%m-%d')
                conn2 = get_db_connection()
                if conn2:
                    cursor2 = conn2.cursor()
                    cursor2.execute("INSERT INTO medical_records (patient_id, doctor_id, appointment_id, date, description) VALUES (%s, %s, %s, %s, %s)",
                                    (patient_id, doc_id_int, None, dt, description))
                    conn2.commit()
                    cursor2.close()
                msg = "Medical record added successfully."
            except Exception as e:
                msg = "Error adding medical record: " + str(e)
        else:
            msg = "All fields are required to add medical record."

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT name FROM patients WHERE id = %s", (patient_id,))
            patient = cursor.fetchone()
            cursor.execute("""
                SELECT mr.id, mr.date, mr.description, d.name as doctor_name
                FROM medical_records mr
                JOIN doctors d ON mr.doctor_id = d.id
                WHERE mr.patient_id = %s
                ORDER BY mr.date DESC
            """, (patient_id,))
            records = cursor.fetchall()
            cursor.execute("SELECT id, name FROM doctors ORDER BY name")
            doctors = cursor.fetchall()
            cursor.close()
        except Exception as e:
            msg = "Error loading medical records: " + str(e)
            doctors = []
        finally:
            conn.close()
    else:
        doctors = []

    return render_template_string(patient_medical_records_template,
                                  patient=patient,
                                  records=records,
                                  doctors=doctors,
                                  msg=msg)

patient_medical_records_template = """
<html>
<head>
  <title>Medical Records for {{patient.name if patient else ''}}</title>
  <style>
    body{font-family: Arial, sans-serif;background:#f0f2f5;margin:0;padding:20px;}
    .container{max-width:800px;margin:20px auto;background:white;padding:20px;border-radius:8px;
      box-shadow:0 2px 8px rgba(0,0,0,0.15);}
    h2{text-align:center;color:#2980b9;}
    table {width: 100%; border-collapse: collapse; margin-top:20px;}
    th, td {border: 1px solid #ccc; padding: 8px; text-align: left;}
    th {background-color:#2980b9; color: white;}
    form {margin-top: 30px;}
    label{display:block;margin-top:10px;font-weight:bold;}
    input[type=date], textarea, select {
      width: 100%; padding: 8px; margin-top:5px; border:1px solid #ccc; border-radius:4px;
      font-size: 14px; font-family: Arial,sans-serif;
    }
    textarea { height: 80px; resize: vertical;}
    button {margin-top: 15px; background-color:#2980b9; border:none; color: white; padding: 10px 15px;
      border-radius:4px; cursor:pointer; font-weight:bold;}
    button:hover {background-color:#1a5d82;}
    .message {color:green; font-weight: bold; margin-top: 15px;}
    a {display: block; margin-top: 20px; text-align:center; color:#3498db; text-decoration:none;}
  </style>
</head>
<body>
  <div class="container">
    <h2>Medical Records for {{patient.name if patient else 'Patient'}}</h2>
    {% if msg %}
      <div class="message">{{ msg }}</div>
    {% endif %}
    {% if records %}
    <table>
      <tr><th>Date</th><th>Doctor</th><th>Description</th></tr>
      {% for record in records %}
        <tr>
          <td>{{ record.date.strftime("%Y-%m-%d") }}</td>
          <td>{{ record.doctor_name }}</td>
          <td>{{ record.description }}</td>
        </tr>
      {% endfor %}
    </table>
    {% else %}
      <p>No medical records found for this patient.</p>
    {% endif %}

    <h3>Add Medical Record</h3>
    <form method="post">
      <label>Date:</label>
      <input type="date" name="date" required>
      <label>Doctor:</label>
      <select name="doctor_id" required>
        <option value="">Select Doctor</option>
        {% for doc in doctors %}
          <option value="{{ doc.id }}">{{ doc.name }}</option>
        {% endfor %}
      </select>
      <label>Description:</label>
      <textarea name="description" required></textarea>
      <button type="submit">Add Record</button>
    </form>

    <a href="{{ url_for('patient_medical_records_list') }}">&larr; Back to Patients List</a>
  </div>
</body>
</html>
"""

@app.route('/appointment/<int:appointment_id>/prescriptions', methods=['GET', 'POST'])
def appointment_prescriptions(appointment_id):
    msg = ""
    conn = get_db_connection()
    prescription_list = []
    appointment = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id, p.name as patient_name, d.name as doctor_name, a.date, a.time
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE a.id = %s
            """, (appointment_id,))
            appointment = cursor.fetchone()
            if request.method == 'POST':
                presc_text = request.form.get('prescription', '').strip()
                if presc_text:
                    cursor.execute("""
                        INSERT INTO prescriptions (appointment_id, doctor_id, patient_id, date, text)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (appointment_id, appointment['doctor_id'], appointment['patient_id'], appointment['date'], presc_text))
                    conn.commit()
                    msg = "Prescription added successfully."
                else:
                    msg = "Prescription text cannot be empty."

            cursor.execute("""
                SELECT id, text, date FROM prescriptions
                WHERE appointment_id = %s
                ORDER BY date DESC
            """, (appointment_id,))
            prescription_list = cursor.fetchall()
            cursor.close()
        except Error as e:
            msg = "Database error: " + str(e)
        finally:
            conn.close()
    else:
        msg = "Failed to connect to database."
    return render_template_string(appointment_prescriptions_template,
                                  appointment=appointment,
                                  prescriptions=prescription_list,
                                  msg=msg)

appointment_prescriptions_template = """
<html>
<head>
  <title>Prescriptions for Appointment #{{ appointment.id if appointment else '' }}</title>
  <style>
    body{font-family: Arial, sans-serif; background:#f0f2f5; margin:0; padding:20px;}
    .container{max-width:700px; margin:auto; background:#fff; padding:20px; border-radius:8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);}
    h2, h3 {text-align:center; color:#2980b9;}
    ul {list-style:none; padding-left:0;}
    li {background:#ecf0f1; margin:8px 0; padding:10px; border-radius:4px;}
    form {margin-top: 20px;}
    textarea {width: 100%; height: 80px; border-radius: 4px; border: 1px solid #ccc; padding: 8px;}
    button {margin-top: 10px; background:#2980b9; color:#fff; border:none; padding:10px 15px;
      border-radius: 4px; cursor:pointer; font-weight: bold;}
    button:hover {background:#1a5d82;}
    .message {color: green; font-weight: bold; margin-top: 10px; text-align: center;}
    a {display: block; margin-top: 20px; text-align:center; text-decoration:none; color:#3498db;}
  </style>
</head>
<body>
  <div class="container">
    <h2>Prescriptions for Appointment #{{ appointment.id if appointment else '' }}</h2>
    {% if appointment %}
    <p><strong>Patient:</strong> {{ appointment.patient_name }}</p>
    <p><strong>Doctor:</strong> {{ appointment.doctor_name }}</p>
    <p><strong>Date & Time:</strong> {{ appointment.date }} {{ appointment.time }}</p>
    {% endif %}

    {% if msg %}
      <div class="message">{{ msg }}</div>
    {% endif %}

    {% if prescriptions %}
      <ul>
        {% for presc in prescriptions %}
          <li><strong>{{ presc.date.strftime("%Y-%m-%d") }}:</strong> {{ presc.text }}</li>
        {% endfor %}
      </ul>
    {% else %}
      <p>No prescriptions found for this appointment.</p>
    {% endif %}

    <h3>Add Prescription</h3>
    <form method="post">
      <textarea name="prescription" placeholder="Enter prescription text" required></textarea>
      <button type="submit">Add Prescription</button>
    </form>

    <a href="{{ url_for('billing') }}">&larr; Back to Billing</a>
  </div>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)
