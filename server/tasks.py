import os
import re
import json
import spacy
import tempfile
import logging
from collections import Counter
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from celery import Celery
from storage import download_to_path
from status_store import StatusStore
from app import db, create_app
from app.models import Document, Job
from datetime import datetime

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("tasks")

# -----------------------------------------------------------------------------
# Celery Configuration
# -----------------------------------------------------------------------------
celery_app = Celery("smart-ocr")
celery_app.config_from_object("celeryconfig")

STATUS = StatusStore()

# -----------------------------------------------------------------------------
# Load NLP Model
# -----------------------------------------------------------------------------
try:
    logger.info("Loading spaCy model 'en_core_web_sm' ...")
    NLP = spacy.load("en_core_web_sm")
    logger.info("spaCy model loaded successfully.")
except Exception as e:
    logger.exception("Failed to load spaCy model: %s", e)
    raise

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using OCR."""
    try:
        logger.info("Starting OCR extraction from PDF: %s", pdf_path)
        texts = []
        images = convert_from_path(pdf_path, dpi=200)
        for i, img in enumerate(images, start=1):
            logger.debug("Processing page %d...", i)
            text = pytesseract.image_to_string(img)
            texts.append(text)
        logger.info("Completed OCR extraction from PDF: %s", pdf_path)
        return "\n".join(texts)
    except Exception as e:
        logger.exception("Error extracting text from PDF: %s", e)
        raise


def extract_text_from_image(img_path: str) -> str:
    """Extract text from a single image using OCR."""
    try:
        logger.info("Starting OCR extraction from image: %s", img_path)
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        logger.info("Completed OCR extraction from image: %s", img_path)
        return text
    except Exception as e:
        logger.exception("Error extracting text from image: %s", e)
        raise


def simple_detect_type(local_path: str) -> str:
    """Detect file type based on extension."""
    lower = local_path.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    elif any(lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff"]):
        return "image"
    return "binary"

# -----------------------------------------------------------------------------
# Tag / Keyword Extraction
# -----------------------------------------------------------------------------
STOPWORDS = set("""
a an and are as at be but by for if in into is it no not of on or such that the their then there these they this to was were will with you your from
""".split())

def extract_tags(text: str, entities: list[dict], k: int = 15) -> list[str]:
    """Extract meaningful tags from text and entities."""
    logger.info("Starting tag extraction...")
    tags = set()

    # 1️⃣ Named Entities
    for e in entities:
        token = e.get("text", "").strip()
        if token:
            tags.add(token)

    # 2️⃣ Noun Chunks
    try:
        doc = NLP(text)
        for nc in doc.noun_chunks:
            t = re.sub(r"[^A-Za-z0-9\- ]+", "", nc.text).strip()
            if t and t.lower() not in STOPWORDS and len(t) > 2:
                tags.add(t)
    except Exception as e:
        logger.warning("Error extracting noun chunks: %s", e)

    # 3️⃣ Frequent Words
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9\-]{3,}", text)]
    words = [w for w in words if w not in STOPWORDS]
    freq = Counter(words).most_common(50)
    for w, _ in freq[:k]:
        tags.add(w)

    # Deduplicate and trim
    cleaned = []
    for t in tags:
        t2 = t.strip()
        if t2 and t2 not in cleaned:
            cleaned.append(t2)

    logger.info("Extracted %d unique tags.", len(cleaned))
    return cleaned[:50]

# -----------------------------------------------------------------------------
# Celery Task: process_document
# -----------------------------------------------------------------------------
# @celery_app.task(queue="ocr")
# def process_document(job_id: str, gcs_uri: str, filename: str):
#     """Performs OCR + NER + Tag extraction + DB persistence."""
#     logger.info("Started processing document job_id=%s, file=%s", job_id, filename)

#     app = create_app()
#     with app.app_context():
#         try:
#             STATUS.update(job_id, status="OCR_IN_PROGRESS",
#                           progress=60, stage="Downloading & OCR")
#             logger.info("[Job %s] Downloading from GCS: %s", job_id, gcs_uri)

#             # ---- 1. Download and OCR ----
#             with tempfile.TemporaryDirectory() as td:
#                 local_path = os.path.join(td, filename)
#                 download_to_path(gcs_uri, local_path)
#                 logger.info("[Job %s] File downloaded to %s", job_id, local_path)

#                 ftype = simple_detect_type(local_path)
#                 logger.info("[Job %s] Detected file type: %s", job_id, ftype)

#                 if ftype == "pdf":
#                     text = extract_text_from_pdf(local_path)
#                 elif ftype == "image":
#                     text = extract_text_from_image(local_path)
#                 else:
#                     logger.warning("[Job %s] Unsupported file type: %s", job_id, ftype)
#                     text = ""

#             # ---- 2. NLP (NER + Tagging) ----
#             STATUS.update(job_id, status="NLP_IN_PROGRESS",
#                           progress=80, stage="Extracting entities & tags")
#             logger.info("[Job %s] Performing NLP entity extraction...", job_id)
#             doc = NLP(text)
#             entities = [
#                 {"text": ent.text, "label": ent.label_,
#                     "start": ent.start_char, "end": ent.end_char}
#                 for ent in doc.ents
#             ]
#             logger.info("[Job %s] Extracted %d entities.", job_id, len(entities))

#             tags = extract_tags(text, entities)
#             logger.info("[Job %s] Extracted %d tags.", job_id, len(tags))

#             # ---- 3. Persist to DB ----
#             logger.info("[Job %s] Saving results to database...", job_id)
#             doc = db.session.query(Document).filter_by(job_id=job_id).first()
#             if doc:
#                 doc.status = "COMPLETED"
#                 doc.text = text[:100000]
#                 doc.entities_json = json.dumps(entities)
#                 doc.tags_json = json.dumps(tags)

#                 db.session.add(doc)
#                 db.session.commit()
#                 logger.info("[Job %s] Document record updated successfully.", job_id)
#             else:
#                 logger.warning("[Job %s] Document not found in DB.", job_id)

#             # ---- 4. Update Status ----
#             STATUS.update(
#                 job_id,
#                 status="COMPLETED",
#                 progress=100,
#                 stage="Done",
#                 text=text[:20000],
#                 entities=json.dumps(entities),
#             )
#             logger.info("[Job %s] Job completed successfully.", job_id)
#             return True

#         except Exception as e:
#             logger.exception("[Job %s] Failed: %s", job_id, e)
#             STATUS.update(job_id, status="FAILED", stage=f"Error: {e}")

#             # Reflect failure in DB as well
#             doc = db.session.query(Document).filter_by(job_id=job_id).first()
#             if doc:
#                 doc.status = "FAILED"

#                 db.session.add(doc)
#                 db.session.commit()
#             logger.error("[Job %s] DB updated with FAILED status.", job_id)

#             raise

@celery_app.task(queue="ocr")
def process_document(job_id: str, gcs_uri: str, filename: str):
    """Performs OCR + NLP + DB persistence."""
    logger.info("Started processing document job_id=%s, file=%s", job_id, filename)

    app = create_app()
    with app.app_context():
        try:
            # -----------------------------------------------------
            # 0. Load DB rows
            # -----------------------------------------------------
            doc_row = db.session.query(Document).filter_by(job_id=job_id).first()
            job_row = db.session.query(Job).filter_by(job_id=job_id).first()

            # Helper to safely update DB job/document
            def update_job(status=None, stage=None, progress=None):
                if job_row:
                    if status: job_row.status = status
                    if stage: job_row.stage = stage
                    if progress is not None: job_row.progress = progress
                    job_row.updated_at = datetime.utcnow()

                if doc_row:
                    if status: doc_row.status = status
                    doc_row.updated_at = datetime.utcnow()

                db.session.commit()

            # -----------------------------------------------------
            # 1. OCR STARTED
            # -----------------------------------------------------
            STATUS.update(job_id,
                          status="OCR_IN_PROGRESS",
                          progress=60,
                          stage="Downloading & OCR")

            update_job(status="OCR_IN_PROGRESS",
                       stage="Downloading & OCR",
                       progress=60)

            logger.info("[Job %s] Downloading from GCS: %s", job_id, gcs_uri)

            # ---- Create temp dir & download ----
            with tempfile.TemporaryDirectory() as td:
                local_path = os.path.join(td, filename)
                download_to_path(gcs_uri, local_path)
                logger.info("[Job %s] File downloaded to %s", job_id, local_path)

                ftype = simple_detect_type(local_path)
                logger.info("[Job %s] Detected file type: %s", job_id, ftype)

                if ftype == "pdf":
                    extracted_text = extract_text_from_pdf(local_path)
                elif ftype == "image":
                    extracted_text = extract_text_from_image(local_path)
                else:
                    logger.warning("[Job %s] Unsupported file type: %s", job_id, ftype)
                    extracted_text = ""

            # -----------------------------------------------------
            # 2. NLP STARTED
            # -----------------------------------------------------
            STATUS.update(job_id,
                          status="NLP_IN_PROGRESS",
                          progress=80,
                          stage="Extracting entities & tags")

            update_job(status="NLP_IN_PROGRESS",
                       stage="Extracting entities & tags",
                       progress=80)

            logger.info("[Job %s] Performing NLP entity extraction...", job_id)

            nlp_doc = NLP(extracted_text)      # rename to avoid conflict with Document model

            entities = [
                {"text": ent.text, "label": ent.label_,
                 "start": ent.start_char, "end": ent.end_char}
                for ent in nlp_doc.ents
            ]

            tags = extract_tags(extracted_text, entities)

            # -----------------------------------------------------
            # 3. Persist to DB
            # -----------------------------------------------------
            logger.info("[Job %s] Saving results to database...", job_id)

            if doc_row:
                doc_row.status = "COMPLETED"
                doc_row.text = extracted_text[:100000]
                doc_row.entities_json = json.dumps(entities)
                doc_row.tags_json = json.dumps(tags)
            else:
                logger.warning("[Job %s] Document row missing!", job_id)

            update_job(status="COMPLETED",
                       stage="Done",
                       progress=100)

            # -----------------------------------------------------
            # 4. Update STATUS store
            # -----------------------------------------------------
            STATUS.update(
                job_id,
                status="COMPLETED",
                progress=100,
                stage="Done",
                text=extracted_text[:20000],
                entities=json.dumps(entities)
            )

            logger.info("[Job %s] Job completed successfully.", job_id)
            return True

        except Exception as e:
            logger.exception("[Job %s] Failed: %s", job_id, e)

            # ---- Update DB on FAIL ----
            if doc_row:
                doc_row.status = "FAILED"

            update_job(status="FAILED",
                       stage=f"Error: {e}",
                       progress=0)

            STATUS.update(job_id, status="FAILED", stage=f"Error: {e}")

            raise