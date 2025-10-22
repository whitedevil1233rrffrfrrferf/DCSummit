from flask import Flask, render_template, request,flash,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from email.message import EmailMessage
import smtplib
import os
from datetime import datetime
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import qrcode
import base64
import uuid
load_dotenv()
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
APP_URL = "https://dcsummit.onrender.com"
app = Flask(__name__)
app.secret_key = 'dc_summit_2025_secret_key_123'
# Configure SQLite database
raw_db_url = os.getenv("DATABASE_URL", "")
clean_db_url = raw_db_url.replace("\n", "").replace("\r", "").strip()

app.config['SQLALCHEMY_DATABASE_URI'] = clean_db_url
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
    contact = db.Column(db.String(20), nullable=False)
    consent = db.Column(db.Boolean, default=False)
    medical_conditions = db.Column(db.Text)

class Verification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_id = db.Column(db.String(50), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    verified_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    id_card = db.Column(db.Boolean, default=False)  # New field

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
            contact = request.form['contact']
            consent = True if request.form.get('consent') == 'yes' else False
            medical_conditions = request.form['medical_conditions']
            allowed_domains=("accountifi.co","qaoncloud.com","desicrew.in")
            if not any(email.endswith(f"@{domain}") for domain in allowed_domains):
                flash('Email must belong to accountifi.co, qaoncloud.com, or desicrew.in domain.', 'danger')
                return redirect(url_for('register'))
            
            if contact == emergency_contact:
                flash('Contact number and emergency contact cannot be the same.', 'danger')
                return redirect(url_for('register'))
            
            existing_emp = Registration.query.filter_by(emp_id=emp_id).first()
            existing_email = Registration.query.filter_by(email=email).first()

            if existing_emp:
                flash('Employee ID already exists.', 'danger')
                return redirect(url_for('register'))

            if existing_email:
                flash('Email address already registered.', 'danger')
                return redirect(url_for('register'))

            ##UNIQUE QR CODE GENERATION

            unique_id = str(uuid.uuid4())
            qr_data = f"https://{request.host}/verify/{emp_id}"
            qr_img = qrcode.make(qr_data)
            qr_dir = os.path.join('static', 'qrcodes')
            os.makedirs(qr_dir, exist_ok=True)
            qr_path = os.path.join(qr_dir, f"{unique_id}.png")
            qr_img.save(qr_path)

            new_reg = Registration(
                full_name=full_name,
                emp_id=emp_id,
                location=location,
                dob=dob,
                email=email,
                business_unit=business_unit,
                contact=contact,
                emergency_contact=emergency_contact,
                consent=consent,
                medical_conditions=medical_conditions
            )

            db.session.add(new_reg)
            db.session.commit()
            send_confirmation_email(email, full_name, qr_path)
            flash('Registration submitted successfully!', 'success')
            return redirect(url_for('register'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')

    return render_template('index.html')

def send_confirmation_email(to_email, name, qr_path):
    # Read the QR image and encode it to base64
    with open(qr_path, 'rb') as f:
        qr_data = f.read()
    encoded_qr = base64.b64encode(qr_data).decode()

    # Create the SendGrid Mail object
    message = Mail(
        from_email='varun@qaoncloud.com',   # must match your verified sender
        to_emails=to_email,
        subject='Registration Successful - Your QR Code',
        html_content=f"""
        <p>Hi {name},</p>
        <p>Thank you for registering for the DC Summit!</p>
        <p>Please find your unique QR code attached below. Scan it at the event for verification.</p>
        <p>DC SUMMIT 2025 Event Registration team</p>
        """
    )

    # Attach the QR code
    from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
    attachment = Attachment(
        FileContent(encoded_qr),
        FileName('your_qr_code.png'),
        FileType('image/png'),
        Disposition('attachment')
    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent successfully! Status: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/verify/<emp_id>')
def verify(emp_id):
    user = Registration.query.filter_by(emp_id=emp_id).first()
    if not user:
        return "<h1>Invalid QR ❌</h1>"

    # Check if already verified in Verification table
    verification = Verification.query.filter_by(emp_id=emp_id).first()
    if not verification:
        verification = Verification(
            emp_id=user.emp_id,
            full_name=user.full_name
        )
        db.session.add(verification)
        db.session.commit()

    return f"<h1>{user.full_name} ({user.emp_id}) is Verified ✅</h1>"

@app.route('/registrations')
def show_registrations():
    registrations = Registration.query.all()
    return render_template('registrations.html', registrations=registrations)

@app.route('/verifications')
def show_verifications():
    verifications = Verification.query.all()
    return render_template('verifications.html', verifications=verifications)

@app.route('/issue_id/<int:verification_id>', methods=['POST'])
def issue_id_card(verification_id):
    verification = Verification.query.get_or_404(verification_id)
    verification.id_card = True
    db.session.commit()
    return redirect(url_for('show_verifications'))


with app.app_context():
    
    db.create_all()
if __name__ == '__main__':
    app.run(debug=True)  # Only used for local testing
