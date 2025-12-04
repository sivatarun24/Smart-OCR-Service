import json
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


# ------------------------------
# Health Check
# ------------------------------
@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


# ------------------------------
# DB Health Check
# ------------------------------
@api_bp.route('/dbhealth', methods=['GET'])
def db_health():
    try:
        # Try to execute a simple query
        db.session.execute(text('SELECT 1'))
        return jsonify({'db_status': 'connected'})
    except Exception as e:
        return jsonify({'db_status': 'disconnected', 'error': str(e)}), 500


# ------------------------------
# Register
# ------------------------------
@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    logger.info(f"Registration attempt: username={username}, email={email}")
    if not username or not email or not name or not password:
        logger.warning("Registration failed: missing fields.")
        return jsonify({'error': 'All fields are required.'}), 400
    if User.query.filter_by(username=username).first():
        logger.warning(f"Registration failed: username already exists ({username})")
        return jsonify({'error': 'Username already exists.'}), 409
    if User.query.filter_by(email=email).first():
        logger.warning(f"Registration failed: email already registered ({email})")
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
    logger.info(f"Registration successful: username={username}, email={email}, id={user.id}")
    return jsonify(user.to_dict()), 201


# ------------------------------
# Login
# ------------------------------
@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    logger.info(f"Login attempt: username={username}")
    if not username or not password:
        logger.warning("Login failed: missing username or password.")
        return jsonify({'error': 'Username and password are required.'}), 400
    try:
        user = User.query.filter_by(username=username).first()
    except Exception as e:
        logger.error(f"Login failed: database error for username={username}: {e}")
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        logger.warning(f"Login failed: invalid credentials for username={username}")
        return jsonify({'error': 'Invalid username or password.'}), 401

    login_user(user)
    logger.info(f"Login successful: username={username}, id={user.id}")
    # Return user info without password_hash
    user_data = user.to_dict()
    user_data.pop('password_hash', None)  # remove sensitive info
    return jsonify({'message': 'Login successful', 'user': user_data}), 200


# ------------------------------
# File Upload
# ------------------------------
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
    

# ------------------------------
# Status Check
# ------------------------------
@api_bp.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    logger.info(f"Fetching status for job_id: {job_id}")
    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        logger.warning(f"Job ID not found: {job_id}")
        return jsonify({"error": f"Job ID '{job_id}' not found"}), 404
    return jsonify(job.to_dict())


# ------------------------------
# OCR Result Retrieval
# ------------------------------
@api_bp.route("/result/<job_id>", methods=["GET"])
def result(job_id):
    logger.info(f"Fetching result for job_id: {job_id}")
    job = Job.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({"error": "not found"}), 404
    if job.status != "COMPLETED":
        logger.info(
            f"Job not completed yet: {job_id}, current status: {job.status}")
        return jsonify({"error": "not ready", "status": job.status}), 409
    doc = Document.query.filter_by(job_id=job_id).first()
    return jsonify({
        "text": doc.text or "",
        "entities": doc.entities_json or "",
        "tags": doc.tags_json or "",
    })


# ------------------------------
# Document Metadata Retrieval
# ------------------------------
@api_bp.route("/doc/<job_id>", methods=["GET"])
def get_doc(job_id):
    logger.info(f"Fetching document details for job_id: {job_id}")
    d = db.session.query(Document).filter_by(job_id=job_id).first()
    if not d:
        logger.warning(f"Document not found: {job_id}")
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": d.id,
        "filename": d.filename,
        "mime": d.mime,
        "gcs_uri": d.gcs_uri,
        "status": d.status,
        "tags": json.loads(d.tags_json or "[]"),
    })


# ------------------------------
# Generate Download Link
# ------------------------------
@api_bp.route("/download/<job_id>", methods=["GET"])
def download_link(job_id):
    logger.info(f"Generating signed URL for job_id: {job_id}")
    d = db.session.query(Document).filter_by(job_id=job_id).first()
    if not d:
        logger.warning(f"Document not found for download: {job_id}")
        return jsonify({"error": "not found"}), 404
    if not d.gcs_uri:
        logger.warning(f"No GCS URI found for document: {job_id}")
        return jsonify({"error": "no file"}), 400
    url = generate_signed_url(d.gcs_uri, minutes=30)
    logger.info(f"Generated signed URL for {job_id}")
    return jsonify({"url": url})


# ------------------------------
# Search Documents
# ------------------------------
@api_bp.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip().lower()
    logger.info(f"Search request received for query: '{q}'")
    if not q:
        return jsonify({"results": []})

    results = []
    docs = db.session.query(Document).all()
    for d in docs:
        hay = " ".join([
            d.filename or "",
            (d.text or "")[:5000].lower(),
            " ".join(json.loads(d.tags_json or "[]")).lower(),
            (d.entities_json or "").lower(),
        ])
        if q in hay:
            results.append({
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "tags": json.loads(d.tags_json or "[]"),
            })
    logger.info(f"Search completed. {len(results)} results found.")
    return jsonify({"results": results})