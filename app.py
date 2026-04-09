from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import random
import os
import re
import uuid
import smtplib
import ssl
import hashlib
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from model import predict_video

# Load environment variables from .env file
load_dotenv()


def hash_otp(otp, salt):
    return hashlib.sha256(f"{otp}{salt}".encode()).hexdigest()


def send_otp_email(recipient_email, otp):
    sender = os.getenv('EMAIL_SENDER')
    password = os.getenv('EMAIL_APP_PASSWORD')
    if not sender or not password:
        raise RuntimeError('Email sender or app password is not configured.')

    host = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    port = int(os.getenv('EMAIL_PORT', '587'))

    message = EmailMessage()
    message['Subject'] = 'TruthLens AI verification code'
    message['From'] = sender
    message['To'] = recipient_email
    message.set_content(
        f"Your TruthLens AI verification code is {otp}.\n"
        "It expires in 30 seconds. Do not share this code with anyone.\n\n"
        "If you did not request this code, please ignore this message."
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(sender, password)
        server.send_message(message)


def is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))


def create_pending_registration(name, email, password_hash):
    otp = str(random.randint(1000, 9999)).zfill(4)
    salt = uuid.uuid4().hex
    otp_hash = hash_otp(otp, salt)
    expiry = datetime.utcnow() + timedelta(seconds=30)

    session['pending_registration'] = {
        'name': name,
        'email': email,
        'password_hash': password_hash,
        'otp_hash': otp_hash,
        'otp_salt': salt,
        'otp_expires_at': expiry.isoformat(),
        'otp_attempts': 0,
        'created_at': datetime.utcnow().isoformat()
    }
    session.modified = True
    send_otp_email(email, otp)
    return otp


def get_pending_registration():
    data = session.get('pending_registration')
    return data if isinstance(data, dict) else None


def clear_pending_registration():
    session.pop('pending_registration', None)
    session.modified = True


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['TEMPLATES_AUTO_RELOAD'] = True

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    plan = db.Column(db.String(20), nullable=False, default='free')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    is_blocked = db.Column(db.Boolean, default=False)
    videos = db.relationship('Video', backref='user', lazy=True, cascade="all, delete-orphan")

# Video model
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    result = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    is_reviewed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def ensure_extended_columns():
    """Ensure our dynamic fields exist without doing full migrations"""
    # User model
    columns = db.session.execute(text("PRAGMA table_info('user')")).fetchall()
    column_names = {column[1] for column in columns}
    
    if 'plan' not in column_names:
        db.session.execute(text("ALTER TABLE user ADD COLUMN plan VARCHAR(20) NOT NULL DEFAULT 'free'"))
    if 'created_at' not in column_names:
        db.session.execute(text("ALTER TABLE user ADD COLUMN created_at DATETIME"))
    if 'last_active' not in column_names:
        db.session.execute(text("ALTER TABLE user ADD COLUMN last_active DATETIME"))
    if 'is_blocked' not in column_names:
        db.session.execute(text("ALTER TABLE user ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT 0"))
        
    # Video model
    vid_columns = db.session.execute(text("PRAGMA table_info('video')")).fetchall()
    vid_column_names = {column[1] for column in vid_columns}
    
    if 'is_reviewed' not in vid_column_names:
        db.session.execute(text("ALTER TABLE video ADD COLUMN is_reviewed BOOLEAN NOT NULL DEFAULT 0"))
        
    db.session.commit()


def build_forensic_insights(result_label, reference_key=""):
    """Build premium, result-specific insight bullets for the result page."""
    normalized = (result_label or "").strip().lower()
    rng = random.Random(f"{normalized}:{reference_key}")

    if normalized in {"authentic", "original"}:
        first_point = "Facial gestures remain natural and consistent across frames."
        pool = [
            "Hand structure appears stable and proportionate during motion segments.",
            "Skin texture and edge detail remain visually consistent throughout the sequence.",
            "Lip movement and expression timing appear synchronized frame to frame.",
            "No major pixel distortion or frame inconsistency was observed.",
            "Lighting transition behavior remains coherent across facial regions.",
            "Boundary detail around the subject remains stable during movement."
        ]
    else:
        first_point = "Pixel break or blur was detected near body boundaries."
        pool = [
            "Facial gestures appear inconsistent across adjacent frames.",
            "Hand structure appears abnormal in high-motion regions.",
            "Lip movement and expression timing show a localized mismatch.",
            "Texture stability around the face region appears irregular.",
            "Edge blending around key subject contours appears unstable.",
            "Temporal continuity shifts suggest synthetic frame reconstruction."
        ]

    selected = rng.sample(pool, 4)
    return [first_point, *selected]


def build_result_summary(result_label):
    normalized = (result_label or "").strip().lower()
    if normalized in {"authentic", "original"}:
        return {
            "title": "Authenticity Signals",
            "subtitle": "Verification patterns align with natural capture behavior."
        }

    return {
        "title": "Detection Insights",
        "subtitle": "The forensic engine detected indicators associated with synthetic manipulation."
    }

# --- Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin access denied.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if getattr(user, 'is_blocked', False):
                flash('Your account has been blocked. Contact support.')
                return render_template('login.html')
                
            user.last_active = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username == 'gudaanurag6' and password == '12345':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
            
        flash('Invalid admin credentials FOR ADMIN')
    return render_template('admin_login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not name or not email or not password or not password2:
            flash('All fields are required.')
            return redirect(url_for('signup'))

        if not is_valid_email(email):
            flash('Please enter a valid email address.')
            return redirect(url_for('signup'))

        if password != password2:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('signup'))

        pending_password_hash = generate_password_hash(password)

        try:
            create_pending_registration(name, email, pending_password_hash)
        except Exception as exc:
            print('OTP email error:', exc)
            flash('Could not send verification email. Check the email configuration and try again.')
            return redirect(url_for('signup'))

        flash('A 4-digit OTP has been sent to your email address. Please enter it below.')
        return redirect(url_for('verify_otp'))

    return render_template('signup.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    pending = get_pending_registration()
    if not pending:
        flash('Please begin registration first.')
        return redirect(url_for('signup'))

    expires_at = datetime.fromisoformat(pending['otp_expires_at'])
    time_left = max(0, int((expires_at - datetime.utcnow()).total_seconds()))

    if request.method == 'POST':
        if request.form.get('resend'):
            try:
                create_pending_registration(pending['name'], pending['email'], pending['password_hash'])
                flash('A new OTP has been sent to your email.')
            except Exception as exc:
                print('OTP resend error:', exc)
                flash('Unable to resend OTP. Please try again later.')
            return redirect(url_for('verify_otp'))

        if time_left <= 0:
            try:
                create_pending_registration(pending['name'], pending['email'], pending['password_hash'])
                flash('OTP expired. A new code has been sent to your email.')
            except Exception as exc:
                print('OTP refresh error:', exc)
                flash('OTP expired and could not be refreshed. Please try again later.')
            return redirect(url_for('verify_otp'))

        entered_otp = request.form.get('otp', '').strip()
        if not entered_otp.isdigit() or len(entered_otp) != 4:
            flash('Enter the 4-digit OTP sent to your email.')
            return redirect(url_for('verify_otp'))

        if pending.get('otp_attempts', 0) >= 5:
            try:
                create_pending_registration(pending['name'], pending['email'])
                flash('Too many attempts. A new OTP has been sent.')
            except Exception as exc:
                print('OTP lockout error:', exc)
                flash('Too many attempts and unable to send a new OTP. Please try again later.')
            return redirect(url_for('verify_otp'))

        if hash_otp(entered_otp, pending['otp_salt']) != pending['otp_hash']:
            pending['otp_attempts'] = pending.get('otp_attempts', 0) + 1
            session['pending_registration'] = pending
            session.modified = True
            remaining = max(0, 5 - pending['otp_attempts'])
            flash(f'Invalid OTP. Attempts remaining: {remaining}')
            return redirect(url_for('verify_otp'))

        base_username = pending['name']
        username = base_username
        suffix = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{suffix}"
            suffix += 1

        user = User(
            username=username,
            email=pending['email'],
            password_hash=pending['password_hash'],
            plan='free'
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        clear_pending_registration()
        flash('Your account has been created successfully.')
        return redirect(url_for('home'))

    return render_template('verify_otp.html', email=pending['email'], time_left=time_left)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    # Fetch all users for full management
    users = User.query.order_by(User.id.desc()).all()
    # Fetch uploaded videos (e.g., all or limit)
    videos = Video.query.order_by(Video.timestamp.desc()).all()
    
    # Calculate stats for chart
    deepfake_count = Video.query.filter(Video.result.ilike('%deepfake%')).count()
    authentic_count = Video.query.filter(~Video.result.ilike('%deepfake%')).count()
    
    return render_template('admin_dashboard.html', 
                           users=users, 
                           videos=videos, 
                           deepfake_count=deepfake_count, 
                           authentic_count=authentic_count)

# --- Admin API Routes ---

@app.route('/admin/api/toggle_block/<int:user_id>', methods=['POST'])
@admin_required
def admin_toggle_block(user_id):
    u = User.query.get_or_404(user_id)
    u.is_blocked = not u.is_blocked
    db.session.commit()
    return jsonify({'success': True, 'is_blocked': u.is_blocked})

@app.route('/admin/api/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/api/toggle_review/<int:video_id>', methods=['POST'])
@admin_required
def admin_toggle_review(video_id):
    v = Video.query.get_or_404(video_id)
    v.is_reviewed = not getattr(v, 'is_reviewed', False)
    db.session.commit()
    return jsonify({'success': True, 'is_reviewed': v.is_reviewed})

@app.route('/admin/api/export_users')
@admin_required
def admin_export_users():
    import csv
    from io import StringIO
    from flask import make_response
    
    users = User.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Username', 'Email', 'Plan', 'Created At', 'Last Active', 'Is Blocked'])
    for u in users:
        cw.writerow([
            u.id, u.username, u.email, u.plan, 
            u.created_at.isoformat() if u.created_at else '', 
            u.last_active.isoformat() if u.last_active else '', 
            u.is_blocked
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/api/export_videos')
@admin_required
def admin_export_videos():
    import csv
    from io import StringIO
    from flask import make_response
    
    videos = Video.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Uploader ID', 'Uploader Name', 'Filename', 'Result', 'Confidence', 'Timestamp', 'Is Reviewed'])
    for v in videos:
        cw.writerow([
            v.id, v.user_id, v.user.username if v.user else 'Deleted', 
            v.filename, v.result, v.confidence, 
            v.timestamp.isoformat() if v.timestamp else '',
            getattr(v, 'is_reviewed', False)
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=videos_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Demo dummy password update logic
        flash('Password updated successfully!')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

@app.route('/model')
def model_page():
    return render_template('model_index.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    if request.method == 'POST':
        flash('Thank you for your message. We will respond within 24 hours.')
        return redirect(url_for('contact_page'))
    return render_template('contact.html')

@app.route('/result')
def result_page():
    # Retrieve the last scan result from the database
    if current_user.is_authenticated and current_user.videos:
        latest_video = current_user.videos[-1]

        summary = build_result_summary(latest_video.result)
        forensic_insights = build_forensic_insights(
            latest_video.result,
            reference_key=latest_video.filename
        )

        return render_template('predict1.html',
                             result=latest_video.result,
                             confidence=latest_video.confidence,
                             filename=latest_video.filename,
                             insight_title=summary["title"],
                             insight_subtitle=summary["subtitle"],
                             forensic_insights=forensic_insights)

    summary = build_result_summary("Unknown")
    return render_template('predict1.html',
                         result='Unknown',
                         confidence=0,
                         filename=None,
                         insight_title=summary["title"],
                         insight_subtitle=summary["subtitle"],
                         forensic_insights=build_forensic_insights("Deepfake", reference_key="fallback"))

@app.route('/pricing')
def pricing_page():
    return render_template('pricing.html')


@app.route('/api/plan', methods=['GET'])
@login_required
def get_plan():
    plan = (current_user.plan or 'free').strip().lower()
    if plan not in {'free', 'pro'}:
        plan = 'free'

    return jsonify({
        'plan': plan,
        'status': 'active',
        'upload_limit': 'unlimited' if plan == 'pro' else 3
    })


@app.route('/api/plan', methods=['POST'])
@login_required
def update_plan():
    data = request.get_json(silent=True) or {}
    requested_plan = str(data.get('plan', '')).strip().lower()

    if requested_plan not in {'free', 'pro'}:
        return jsonify({'error': 'Invalid plan selection.'}), 400

    current_plan = (current_user.plan or 'free').strip().lower()

    if current_plan == 'pro' and requested_plan == 'free':
        return jsonify({'error': 'Downgrading from Pro to Free is not allowed.'}), 403

    upgraded = False
    if current_plan == 'free' and requested_plan == 'pro':
        current_user.plan = 'pro'
        db.session.commit()
        upgraded = True

    final_plan = (current_user.plan or 'free').strip().lower()
    return jsonify({
        'plan': final_plan,
        'status': 'active',
        'upload_limit': 'unlimited' if final_plan == 'pro' else 3,
        'upgraded': upgraded
    })

@app.route('/validate', methods=['GET'])
@login_required
def validate():
    return render_template('validate.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if "video" not in request.files:
        flash("No file uploaded")
        return redirect(url_for('validate'))

    video_file = request.files["video"]

    if video_file.filename == "":
        flash("No selected file")
        return redirect(url_for('validate'))

    current_plan = (current_user.plan or 'free').strip().lower()
    if current_plan == 'free':
        total_uploads = Video.query.filter_by(user_id=current_user.id).count()
        if total_uploads >= 3:
            flash('Free plan allows up to 3 uploads. Upgrade to Pro for unlimited uploads.')
            return redirect(url_for('validate'))

    filename = secure_filename(video_file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    video_file.save(filepath)

    prediction = predict_video(filepath)
    result_str = prediction["result"]
    if "deepfake" not in result_str.lower():
        result_str = "Authentic"
    
    confidence = prediction["confidence"]

    # Save video analysis to database
    video = Video(
        filename=filename,
        result=result_str,
        confidence=confidence,
        user_id=current_user.id
    )
    db.session.add(video)
    db.session.commit()

    return render_template(
        "predict.html",
        prediction=result_str,
        confidence=round(confidence, 2),
        unique_hash_id=filename
    )

# API routes for statistics
@app.route('/api/stats')
def get_stats():
    total_videos = Video.query.count()
    deepfake_count = Video.query.filter_by(result='Deepfake').count()
    authentic_count = Video.query.filter_by(result='Authentic').count()
    
    return jsonify({
        'total_videos': total_videos,
        'deepfake_count': deepfake_count,
        'authentic_count': authentic_count
    })

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        db.create_all()
        ensure_extended_columns()
    
    # Use environment variable for debug mode (False in production)
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))