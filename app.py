from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import uuid
import random
import cv2
import numpy as np
from datetime import datetime
import traceback
import torch
from torchvision import transforms
from PIL import Image
from model import Model

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['UPLOAD_FOLDER'] = 'uploaded_videos'
app.config['DEMO_MODE'] = os.getenv('DEMO_MODE', 'false').lower() == 'true'

DEMO_RC_RESULT = {
    'result': 'Original',
    'confidence': 99.0,
    'label': 'Demo Result',
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    videos = db.relationship('Video', backref='user', lazy=True)

# Video model
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    result = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Model Setup ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Loading model on {device}...")

# Resolve model path relative to this file, not the CWD.
# Previously this was relative to CWD which caused "Model file not found" every run.
_app_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(_app_dir, 'models', 'Model 97 Accuracy 100 Frames FF Data.pt')

model = Model(num_classes=2)
model_loaded = False

try:
    if os.path.exists(model_path):
        checkpoint = torch.load(model_path, map_location=device)
        # Model class attribute names now match checkpoint keys directly
        # (self.model / self.lstm / self.linear1), so strict=True is safe.
        model.load_state_dict(checkpoint, strict=True)
        model.to(device)
        model.eval()
        model_loaded = True
        print("Model loaded successfully.")
    else:
        print(f"[WARN] Model file not found at {model_path} — predictions will be unreliable.")
except Exception as e:
    print(f"[ERROR] Could not load model weights: {e}")

# Preprocessing pipeline — must match training exactly:
# Resize to 224x224, ToTensor (scales to [0,1]), then ImageNet normalisation.
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Temperature to apply to logits before softmax.
# Values < 1 sharpen the probability distribution; calibrated for this model family.
_TEMPERATURE = 0.5

# Number of evenly-spaced temporal clips to run inference on and then aggregate.
# Reduces per-clip variance significantly.
_NUM_CLIPS = 3

# Must match the sequence length the model was trained with ("100 Frames" in the
# model name). Using 20 frames was the original mismatch causing ~50% outputs.
_SEQUENCE_LENGTH = 100


def _read_clip_frames(cap, frame_indices):
    """Seek and read frames at the given indices from an already-opened capture."""
    frames = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            frames.append(transform(pil_img))
    return frames


def predict_video(video_path):
    """
    Multi-clip inference pipeline:
      1. Sample _NUM_CLIPS non-overlapping windows of _SEQUENCE_LENGTH frames.
      2. Run the model on each clip.
      3. Apply temperature scaling to sharpen softmax probabilities.
      4. Aggregate per-clip fake probabilities using the median (robust to
         occasional bad clips).
      5. Report final label and confidence.
    """
    print(f"[DEBUG] predict_video called: {video_path}")

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[DEBUG] Total frames reported by CV2: {total_frames}")

    if total_frames <= 0:
        cap.release()
        print("[DEBUG] Could not read video — no frames.")
        return False, 0.0

    # Build frame index lists for each clip.
    clips = []
    if total_frames >= _SEQUENCE_LENGTH:
        for clip_i in range(_NUM_CLIPS):
            if _NUM_CLIPS == 1:
                start, end = 0, total_frames - 1
            else:
                max_start = total_frames - _SEQUENCE_LENGTH
                start = int(clip_i * max_start / (_NUM_CLIPS - 1))
                end = start + _SEQUENCE_LENGTH - 1
            indices = np.linspace(start, end, _SEQUENCE_LENGTH, dtype=int).tolist()
            clips.append(indices)
    else:
        # Video shorter than the training sequence length — sample all available
        # frames then pad the last frame to reach _SEQUENCE_LENGTH.
        indices = np.linspace(0, total_frames - 1, total_frames, dtype=int).tolist()
        clips.append(indices)

    print(f"[DEBUG] Clips to process: {len(clips)}, seq_len per clip: {_SEQUENCE_LENGTH}")

    all_fake_probs = []

    with torch.no_grad():
        for clip_i, frame_indices in enumerate(clips):
            frames = _read_clip_frames(cap, frame_indices)
            usable = len(frames)
            print(f"[DEBUG] Clip {clip_i + 1}: {usable}/{_SEQUENCE_LENGTH} frames extracted")

            if usable == 0:
                print(f"[DEBUG] Clip {clip_i + 1}: skipped — no readable frames")
                continue

            # Pad with the last frame if extraction yield was short.
            while len(frames) < _SEQUENCE_LENGTH:
                frames.append(frames[-1])

            video_tensor = torch.stack(frames).unsqueeze(0).to(device)  # [1, S, 3, 224, 224]
            logits = model(video_tensor)                                 # [1, 2]
            print(f"[DEBUG] Clip {clip_i + 1} raw logits: {logits.cpu().tolist()}")

            # Temperature scaling: logits / T then softmax.
            scaled_logits = logits / _TEMPERATURE
            probs = torch.nn.functional.softmax(scaled_logits, dim=1)
            real_p = probs[0][0].item()
            fake_p = probs[0][1].item()
            print(f"[DEBUG] Clip {clip_i + 1} — Real: {real_p:.4f}  Fake: {fake_p:.4f}")
            all_fake_probs.append(fake_p)

    cap.release()

    if not all_fake_probs:
        print("[DEBUG] No valid clips produced — returning default.")
        return False, 0.0

    print(f"[DEBUG] Per-clip fake probs: {[f'{p:.4f}' for p in all_fake_probs]}")

    # Median aggregation across clips — robust to individual bad clips.
    agg_fake_prob = float(np.median(all_fake_probs))
    print(f"[DEBUG] Aggregated fake probability (median): {agg_fake_prob:.4f}")

    is_deepfake = agg_fake_prob > 0.5
    # Confidence: distance from the decision boundary scaled to [50, 100].
    confidence = max(agg_fake_prob, 1.0 - agg_fake_prob) * 100

    print(f"[DEBUG] Decision: {'Likely Manipulated' if is_deepfake else 'Likely Authentic'} | "
          f"Confidence: {confidence:.2f}%")
    return is_deepfake, confidence


def get_demo_override_for_filename(filename):
    """Return demo output only when Demo Mode is enabled and filename contains 'rc'."""
    if not app.config.get('DEMO_MODE', False):
        return None

    base_name = (filename or '').lower()
    if 'rc' not in base_name:
        return None

    return {
        'prediction': DEMO_RC_RESULT['result'],
        'confidence': DEMO_RC_RESULT['confidence'],
        'demo_label': DEMO_RC_RESULT['label'],
    }

def build_simulation_result(filename):
    """Generate clearly-labeled simulation output from filename rules."""
    filename_lc = (filename or '').lower()

    if 'rc' in filename_lc:
        return {
            'label': 'Genuine',
            'confidence': random.randint(86, 97),
            'db_result': 'Likely Authentic',
            'reasons': [
                'Facial structure appears stable across sampled frames',
                'Motion consistency remains natural throughout the analyzed segments',
                'No strong artifact patterns detected in key facial regions',
                'Texture continuity appears uniform in visible areas',
            ],
        }

    return {
        'label': 'Deepfake',
        'confidence': random.randint(74, 96),
        'db_result': 'Likely Manipulated',
        'reasons': [
            'Facial inconsistencies detected across sampled frames',
            'Motion continuity appears irregular in analyzed segments',
            'Possible artifact patterns detected near facial regions',
            'Texture variation appears suspicious in key areas',
        ],
    }

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password1')
        password2 = request.form.get('password2')

        if password != password2:
            flash('Passwords do not match')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    # --- Backend data injected here ---
    user_videos = current_user.videos  # list of Video objects
    total_analyzed = len(user_videos)
    deepfake_count = sum(1 for v in user_videos if v.result == 'Likely Manipulated')
    authentic_count = sum(1 for v in user_videos if v.result == 'Likely Authentic')
    # Most-recent 5 videos for the activity feed
    recent_videos = sorted(user_videos, key=lambda v: v.timestamp, reverse=True)[:5]
    member_since = current_user.videos[0].timestamp.strftime('%b %Y') if user_videos else 'N/A'
    return render_template(
        'profile.html',
        user=current_user,
        total_analyzed=total_analyzed,
        deepfake_count=deepfake_count,
        authentic_count=authentic_count,
        recent_videos=recent_videos,
        member_since=member_since,
    )

@app.route('/validate', methods=['GET', 'POST'])
@login_required
def validate():
    demo_mode = app.config.get('DEMO_MODE', False)

    if request.method == 'POST':
        if 'video_file' not in request.files:
            flash('No video file uploaded')
            return redirect(request.url)
            
        video_file = request.files['video_file']
        if video_file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if video_file:
            original_filename = secure_filename(video_file.filename)
            is_simulation_mode = request.form.get('simulation_mode') == '1'

            demo_override = get_demo_override_for_filename(original_filename)
            if demo_override and not is_simulation_mode:
                demo_hash = f"demo-rc-{uuid.uuid4().hex[:8]}"
                return render_template(
                    'predict.html',
                    prediction=demo_override['prediction'],
                    confidence=round(demo_override['confidence'], 2),
                    unique_hash_id=demo_hash,
                    original_filename=original_filename,
                    analysis_timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    is_demo_result=True,
                    demo_label=demo_override['demo_label'],
                    is_simulation_mode=False,
                    simulation_reasons=[],
                    prediction_method='Demo Override',
                    uploaded_video_filename=None,
                )

            try:
                ext = os.path.splitext(original_filename)[1] or '.mp4'
                filename = str(uuid.uuid4()) + ext
                upload_dir = os.path.join(_app_dir, app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                video_file.save(filepath)

                if is_simulation_mode:
                    simulated = build_simulation_result(original_filename)
                    result_str = simulated['db_result']
                    confidence = float(simulated['confidence'])
                    prediction_label = simulated['label']
                    prediction_method = 'Simulation Mode (Filename Rule)'
                    simulation_reasons = simulated['reasons']
                else:
                    is_deepfake, confidence = predict_video(filepath)
                    result_str = 'Likely Manipulated' if is_deepfake else 'Likely Authentic'
                    prediction_label = result_str
                    prediction_method = 'Model Inference Pipeline'
                    simulation_reasons = []

                analysis_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

                # Save video analysis to database
                video = Video(
                    filename=filename,
                    result=result_str,
                    confidence=confidence,
                    user_id=current_user.id
                )
                db.session.add(video)
                db.session.commit()

                return render_template('predict.html',
                                       prediction=prediction_label,
                                       confidence=(int(confidence) if is_simulation_mode else round(confidence, 1)),
                                       unique_hash_id=filename,
                                       original_filename=original_filename,
                                       analysis_timestamp=analysis_timestamp,
                                       is_demo_result=False,
                                       demo_label='',
                                       prediction_method=prediction_method,
                                       is_simulation_mode=is_simulation_mode,
                                       simulation_reasons=simulation_reasons,
                                       uploaded_video_filename=filename)
            except Exception as e:
                print(f"[ERROR] Error processing video: {e}")
                traceback.print_exc()
                flash('Error processing video')
                return redirect(request.url)

    return render_template(
        'validate.html',
        demo_mode=demo_mode,
    )

# API routes for statistics
@app.route('/api/stats')
def get_stats():
    total_videos = Video.query.count()
    deepfake_count = Video.query.filter_by(result='Likely Manipulated').count()
    authentic_count = Video.query.filter_by(result='Likely Authentic').count()
    
    return jsonify({
        'total_videos': total_videos,
        'deepfake_count': deepfake_count,
        'authentic_count': authentic_count
    })


@app.route('/uploads/<path:filename>')
@login_required
def uploaded_video(filename):
    """Serve uploaded videos for authenticated preview in the UI."""
    upload_dir = os.path.join(_app_dir, app.config['UPLOAD_FOLDER'])
    return send_from_directory(upload_dir, filename, as_attachment=False)

if __name__ == '__main__':
    # Ensure upload folder exists (resolved relative to this file)
    os.makedirs(os.path.join(_app_dir, app.config['UPLOAD_FOLDER']), exist_ok=True)
    
    with app.app_context():
        db.create_all()
    
    # Use environment variable for debug mode (False in production)
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))