from flask import Flask, render_template, request,flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from email.message import EmailMessage
import smtplib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dc_summit_2025_secret_key_123'
# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registrations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    emp_id = db.Column(db.String(50), nullable=False, unique=True)
    location = db.Column(db.String(100))
    dob = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    business_unit = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(20))
    consent = db.Column(db.Boolean, default=False)
    medical_conditions = db.Column(db.Text)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST','GET'])
def register():
    if request.method == 'POST':
        try:
            full_name = request.form['full_name']
            emp_id = request.form['emp_id']
            location = request.form['location']
            dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            email = request.form['email']
            business_unit = request.form['business_unit']
            emergency_contact = request.form['emergency_contact']
            consent = True if request.form.get('consent') == 'yes' else False
            medical_conditions = request.form['medical_conditions']

            new_reg = Registration(
                full_name=full_name,
                emp_id=emp_id,
                location=location,
                dob=dob,
                email=email,
                business_unit=business_unit,
                emergency_contact=emergency_contact,
                consent=consent,
                medical_conditions=medical_conditions
            )

            db.session.add(new_reg)
            db.session.commit()
            send_confirmation_email(email, full_name)
            flash('Registration submitted successfully!', 'success')
            return redirect(url_for('register'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')

    return render_template('index.html')

@app.route('/registrations')
def registrations():
    all_users = Registration.query.all()
    return render_template('registrations.html', users=all_users)

# Email sending function
def send_confirmation_email(to_email, name):
    msg = EmailMessage()
    msg['Subject'] = 'Registration Successful'
    msg['From'] = 'varun@qaoncloud.com'
    msg['To'] = to_email
    msg.set_content(f"Hi {name},\n\nThank you for registering!\n\n- QAonCloud Team")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('varun@qaoncloud.com', 'mcfzcfpuxchnzrll')  # app password
        smtp.send_message(msg)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
