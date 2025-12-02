from flask import Blueprint, request, jsonify
import logging
from sqlalchemy import text
from .models import User
from . import db, bcrypt

from status_store import StatusStore
from werkzeug.utils import secure_filename
from .models import Document
from storage import upload_file, generate_signed_url
from tasks import process_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

STATUS = StatusStore()

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
    user = User(username=username, email=email, name=name, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

# add code for the login route
@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200

# create a simple /api/upload
@api_bp.route('/upload', methods=['POST'])
def upload():
    logger.info("Received upload request.")
    if "file" not in request.files:
        logger.warning("Upload failed: No file part in request.")
        return jsonify({"error": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        logger.warning("Upload failed: No selected file.")
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(f.filename)
    job_id = STATUS.new_job(filename)
    logger.info(f"Starting new job: {job_id}, filename: {filename}")

    try:
        doc = Document(
            job_id=job_id,
            filename=filename,
            mime=f.mimetype or "",
            gcs_uri="",  # Will be set after upload
            status="UPLOADING",
        )
        db.session.add(doc)
        db.session.commit()
        STATUS.update(job_id, status="UPLOADING",
                      progress=20, stage="Uploading to GCS")

        dest = f"uploads/{job_id}/{filename}"
        logger.info(f"Uploading file to GCS path: {dest}")
        gcs_uri = upload_file(f, dest, content_type=f.mimetype)

        STATUS.update(job_id, status="QUEUED", progress=40,
                      stage="Queued for OCR", gcs_uri=gcs_uri)
        logger.info(
            f"File uploaded successfully: {gcs_uri}. Enqueuing OCR job...")

        # Enqueue OCR task
        process_document.delay(job_id, gcs_uri, filename)
        return jsonify({"job_id": job_id})
    except Exception as e:
        logger.exception("Error during file upload.")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500