from flask import Blueprint, request, jsonify
import logging
from sqlalchemy import text
from .models import Job, User
from . import db, bcrypt

from status_store import StatusStore
from werkzeug.utils import secure_filename
from .models import Document
from storage import upload_file, generate_signed_url
from tasks import process_document
from datetime import datetime
from flask_login import login_required, login_user, login_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
api_bp = Blueprint('api', __name__, url_prefix='/api')

STATUS = StatusStore()

# --- Flask-Login user loader ---
# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))

# write a silple /api/health to get the status
@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# write a simple /api/dbhealth to check database connection
@api_bp.route('/dbhealth', methods=['GET'])
def db_health():
    try:
        # Try to execute a simple query
        db.session.execute(text('SELECT 1'))
        return jsonify({'db_status': 'connected'})
    except Exception as e:
        return jsonify({'db_status': 'disconnected', 'error': str(e)}), 500

@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    if not username or not email or not name or not password:
        return jsonify({'error': 'All fields are required.'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists.'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 409
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(
        username=username, 
        email=email, 
        name=name, 
        password_hash=password_hash
        )
    db.session.add(user)
    db.session.commit()
    # db.session.expunge(user)  # detach from session
    return jsonify(user.to_dict()), 201

# add code for the login route
@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400
    
    try:
        user = User.query.filter_by(username=username).first()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid username or password.'}), 401
    
    # Optional: log the user in for session management
    login_user(user)
    
    # Return user info without password_hash
    user_data = user.to_dict()
    user_data.pop('password_hash', None)  # remove sensitive info
    
    return jsonify({'message': 'Login successful', 'user': user_data}), 200

# create a simple /api/upload
@api_bp.route('/upload', methods=['POST'])
# @login_required
def upload():
    logger.info("Received upload request.")

    # Validate file exists
    if "file" not in request.files:
        logger.warning("No file part in request.")
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        logger.warning("No selected file.")
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(f.filename)
    job_id = STATUS.new_job(filename)

    logger.info(f"Starting new job: {job_id}, filename={filename}")

    try:
        # ---- STEP 1: Create Document row ----
        doc = Document(
            job_id=job_id,
            filename=filename,
            mime=f.mimetype or "",
            gcs_uri="",
            status="UPLOADING",
            user_id=getattr(request, "user_id", None)  # optional user linking
        )

        db.session.add(doc)
        db.session.flush()

        # Create Job row
        job = Job(
            job_id=job_id,
            filename=filename,
            mime=f.mimetype or "",
            gcs_uri="",
            status="UPLOADING",
            progress=20,
            stage="Uploading to GCS",
            document_id=doc.id
        )
        db.session.add(job)

        logger.info(f"Document row created in DB (id={doc.id})")

        STATUS.update(job_id, status="UPLOADING", progress=20, stage="Uploading to GCS")

        # ---- STEP 2: Upload file to cloud storage ----
        dest = f"uploads/{job_id}/{filename}"
        logger.info(f"Uploading file to GCS: {dest}")

        gcs_uri = upload_file(f, dest, content_type=f.mimetype)
        logger.info(f"Uploaded to GCS: {gcs_uri}")

        # ---- STEP 3: Update Document DB row after GCS upload ----
        logger.info("Fetching document to update...")

        # Update document
        doc = Document.query.filter_by(job_id=job_id).first()
        doc.gcs_uri = gcs_uri
        doc.status = "QUEUED"
        doc.updated_at = datetime.utcnow()

        # Update job table
        job = Job.query.filter_by(job_id=job_id).first()
        job.gcs_uri = gcs_uri
        job.status = "QUEUED"
        job.progress = 40
        job.stage = "Queued for OCR"
        job.updated_at = datetime.utcnow()

        db.session.commit()
        logger.info("Document updated in DB after GCS upload.")

        STATUS.update(job_id, status="QUEUED", progress=40, stage="Queued for OCR", gcs_uri=gcs_uri)

        # ---- STEP 4: Enqueue OCR task ----
        logger.info("Sending OCR task to Celery worker...")
        process_document.delay(job_id, gcs_uri, filename)

        return jsonify({"job_id": job_id}), 200

    except Exception as e:
        logger.exception("Error during /upload processing.")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500