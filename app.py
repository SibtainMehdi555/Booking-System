import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from email_validator import validate_email, EmailNotValidError
import secrets
from flask_session import Session
from dotenv import load_dotenv
from utils.xml_validator import validate_areas_xml
from utils.pdf_generator import generate_booking_summary_pdf

load_dotenv()

# --- CONFIGURATION ---
app = Flask(__name__)
# Generate a random secret key
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parakai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email config (use your SMTP details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'my_app_session:'
app.config['SESSION_FILE_DIR'] = './instance/flask_session'

Session(app)

db = SQLAlchemy(app)
# mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Firebase Config (using environment variables)
FIREBASE_CONFIG = {
  "apiKey": os.getenv('FIREBASE_API_KEY'),
  "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
  "projectId": os.getenv('FIREBASE_PROJECT_ID'),
  "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
  "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
  "appId": os.getenv('FIREBASE_APP_ID'),
  "measurementId": os.getenv('FIREBASE_MEASUREMENT_ID') # Optional
}

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def get_id(self):
        return str(self.id)

class Area(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    cost_per_day = db.Column(db.Float, nullable=False)
    booked = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(200))
    description = db.Column(db.Text)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_name = db.Column(db.String(120), nullable=False)
    area_id = db.Column(db.String(10), db.ForeignKey('area.id'))
    area_name = db.Column(db.String(120))
    group_size = db.Column(db.Integer, nullable=False)
    check_in_date = db.Column(db.String(20), nullable=False)
    check_out_date = db.Column(db.String(20), nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    area_capacity = db.Column(db.Integer, nullable=False)
    cost_per_day = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user_name,
            'area_id': self.area_id,
            'area_name': self.area_name,
            'group_size': self.group_size,
            'check_in_date': self.check_in_date,
            'check_out_date': self.check_out_date,
            'total_cost': self.total_cost,
            'area_capacity': self.area_capacity,
            'cost_per_day': self.cost_per_day,
            'image_path': self.image_path,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

# --- LOGIN MANAGER ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

def get_areas():
    try:
        areas = Area.query.all()
        return [{
            'id': area.id,
            'name': area.name,
            'capacity': area.capacity,
            'cost_per_day': area.cost_per_day,
            'booked': area.booked,
            'image_path': area.image_path,
            'description': area.description
        } for area in areas]
    except Exception as e:
        print(f"Error getting areas: {e}")
        return []

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('welcome.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')
            
        try:
            validate_email(email)
        except EmailNotValidError:
            flash('Invalid email address', 'danger')
            return render_template('signup.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('signup.html')
            
        # Create user
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        # Log the user in immediately after signup
        login_user(user)
        
        flash('Registration successful! You are now logged in.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
            
        flash('Invalid email or password', 'danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('dashboard.html', bookings=bookings, user=current_user)

@app.route('/book')
@login_required
def book_area_page():
    # You will need to create templates/book_area.html
    return render_template('book_area.html')

@app.route('/summary')
@login_required
def view_booking_summary():
    # You will need to create templates/booking_summary.html
    # You might also pass booking data to the template here
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('booking_summary.html', bookings=bookings)

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/api/areas')
def api_get_areas():
    areas = get_areas()
    return jsonify(areas)

@app.route('/api/calculate_cost', methods=['POST'])
@login_required
def calculate_cost():
    data = request.get_json()
    area_id = data.get('area_id')
    try:
        check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d')
        check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d')
    except ValueError:
         return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    group_size = int(data.get('group_size'))
    
    area = Area.query.get(area_id)
    if not area:
        return jsonify({'error': 'Area not found'}), 404
    
    if area.booked:
        return jsonify({'error': 'Area is already booked'}), 400
    
    if group_size > area.capacity:
        return jsonify({'error': 'Group size exceeds area capacity'}), 400
    
    days = (check_out - check_in).days
    if days <= 0:
         return jsonify({'error': 'Check-out date must be after check-in date.'}), 400
    total_cost = area.cost_per_day * days
    
    return jsonify({
        'area_name': area.name,
        'days': days,
        'cost_per_day': area.cost_per_day,
        'total_cost': total_cost
    })

@app.route('/api/book', methods=['POST'])
@login_required
def book_area():
    try:
        data = request.get_json()
        area_id = data.get('area_id')
        check_in_str = data.get('check_in')
        check_out_str = data.get('check_out')
        group_size = int(data.get('group_size'))
        
        # Get area from database
        area = Area.query.get(area_id)
        if not area:
            return jsonify({'error': 'Area not found'}), 404
        
        # Check if area is already booked
        if area.booked:
            return jsonify({'error': 'Area is already booked'}), 400
        
        # Validate dates
        try:
            check_in_dt = datetime.strptime(check_in_str, '%Y-%m-%d')
            check_out_dt = datetime.strptime(check_out_str, '%Y-%m-%d')
            
            if check_in_dt < datetime.now():
                return jsonify({'error': 'Check-in date cannot be in the past'}), 400
                
            if check_out_dt <= check_in_dt:
                return jsonify({'error': 'Check-out date must be after check-in date'}), 400
                
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Validate group size
        if group_size <= 0:
            return jsonify({'error': 'Group size must be greater than 0'}), 400
            
        if group_size > area.capacity:
            return jsonify({'error': f'Group size exceeds area capacity of {area.capacity}'}), 400
        
        # Calculate total cost
        days = (check_out_dt - check_in_dt).days
        total_cost = area.cost_per_day * days
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            user_name=current_user.name,
            area_id=area_id,
            area_name=area.name,
            group_size=group_size,
            check_in_date=check_in_str,
            check_out_date=check_out_str,
            total_cost=total_cost,
            area_capacity=area.capacity,
            cost_per_day=area.cost_per_day,
            image_path=area.image_path,
            status='pending'
        )
        
        # Mark area as booked
        area.booked = True
        
        # Save to database
        db.session.add(booking)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Booking successful',
            'booking': booking.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/my_bookings')
@login_required
def api_my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return jsonify([booking.to_dict() for booking in bookings])

# --- NEW SIDEBAR ROUTES ---
@app.route('/clients')
@login_required
def clients():
    return render_template('clients.html')

@app.route('/employees')
@login_required
def employees():
    return render_template('employees.html')

@app.route('/schedule')
@login_required
def schedule():
    return render_template('schedule.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/booking/<int:booking_id>/pdf')
@login_required
def generate_booking_pdf(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure the booking belongs to the current user
    if booking.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Create PDF
    booking_data = {
        'id': booking.id,
        'area_name': booking.area_name,
        'start_date': booking.check_in_date,
        'end_date': booking.check_out_date,
        'people': booking.group_size,
        'total_cost': booking.total_cost,
        'status': booking.status
    }
    
    # Create PDFs directory if it doesn't exist
    pdf_dir = os.path.join(app.static_folder, 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Generate PDF
    pdf_path = os.path.join(pdf_dir, f'booking_{booking_id}.pdf')
    generate_booking_summary_pdf(booking_data, pdf_path)
    
    # Return the PDF file
    return send_file(pdf_path, as_attachment=True, download_name=f'booking_{booking_id}.pdf')

@app.route('/api/welcome-booking', methods=['POST'])
def welcome_booking():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'contact', 'message', 'dateFrom', 'dateTo']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate dates
        try:
            date_from = datetime.strptime(data['dateFrom'], '%Y-%m-%d')
            date_to = datetime.strptime(data['dateTo'], '%Y-%m-%d')
            
            if date_to < date_from:
                return jsonify({'error': 'End date must be after start date'}), 400
                
            if date_from < datetime.now():
                return jsonify({'error': 'Start date cannot be in the past'}), 400
                
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
        
        # If user is logged in, create a booking
        if current_user.is_authenticated:
            # Create a new booking
            booking = Booking(
                user_id=current_user.id,
                user_name=current_user.name,
                area_name="General Inquiry",  # Default area for welcome page bookings
                group_size=1,  # Default to 1 for general inquiries
                check_in_date=data['dateFrom'],
                check_out_date=data['dateTo'],
                total_cost=0,  # Will be calculated later
                status='pending'
            )
            db.session.add(booking)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Booking request submitted successfully',
                'booking_id': booking.id
            })
        else:
            # Store in session for later processing
            if 'pending_bookings' not in session:
                session['pending_bookings'] = []
                
            session['pending_bookings'].append({
                'firstName': data['firstName'],
                'lastName': data['lastName'],
                'contact': data['contact'],
                'message': data['message'],
                'dateFrom': data['dateFrom'],
                'dateTo': data['dateTo']
            })
            session.modified = True
            
            return jsonify({
                'success': True,
                'message': 'Booking request received. Please sign up or log in to complete your booking.',
                'requires_auth': True
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-booking', methods=['POST'])
@login_required
def save_booking():
    try:
        # Get the XML data from the request
        xml_data = request.get_data()
        
        # Validate the XML structure
        try:
            ET.fromstring(xml_data)
        except ET.ParseError:
            return jsonify({'success': False, 'message': 'Invalid XML format'}), 400
            
        # Save the XML file
        with open('data/bookings.xml', 'wb') as f:
            f.write(xml_data)
            
        return jsonify({'success': True, 'message': 'Booking saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- INITIALIZE DB ---
def migrate_areas_from_xml():
    try:
        xml_path = 'data/reserved_areas.xml'
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        for area in root.findall('area'):
            # Check if area already exists
            existing_area = Area.query.get(area.get('id'))
            if not existing_area:
                new_area = Area(
                    id=area.get('id'),
                    name=area.get('name'),
                    capacity=int(area.get('capacity')),
                    cost_per_day=float(area.get('cost_per_day')),
                    booked=area.get('booked') == 'true',
                    image_path=area.get('image_path'),
                    description=area.find('description').text
                )
                db.session.add(new_area)
        
        db.session.commit()
        print("Areas migrated successfully!")
    except Exception as e:
        print(f"Error migrating areas: {e}")
        db.session.rollback()

def init_db():
    with app.app_context():
        db.create_all()
        migrate_areas_from_xml()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True) 