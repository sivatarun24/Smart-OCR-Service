import os
import logging
from google.cloud import storage
from datetime import timedelta

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("storage")

# -----------------------------------------------------------------------------
# Environment Variables
# -----------------------------------------------------------------------------
BUCKET = os.environ.get("GCS_BUCKET")
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")

if not BUCKET:
    logger.warning("Environment variable 'GCS_BUCKET' is not set.")
if not PROJECT_ID:
    logger.warning("Environment variable 'GCP_PROJECT_ID' is not set.")

_client = None

# -----------------------------------------------------------------------------
# GCS Client
# -----------------------------------------------------------------------------


def client():
    """Return a singleton Google Cloud Storage client."""
    global _client
    if _client is None:
        try:
            _client = storage.Client(project=PROJECT_ID)
            logger.info(
                "Initialized Google Cloud Storage client for project: %s", PROJECT_ID)
        except Exception as e:
            logger.exception("Failed to initialize GCS client: %s", e)
            raise
    return _client

# -----------------------------------------------------------------------------
# Upload File
# -----------------------------------------------------------------------------


def upload_file(fileobj, dest_path: str, content_type: str | None = None) -> str:
    """
    Upload a file object to GCS.
    Returns the gs:// path of the uploaded object.
    """
    try:
        bucket = client().bucket(BUCKET)
        blob = bucket.blob(dest_path)
        logger.info("Uploading file to GCS: bucket=%s, path=%s",
                    BUCKET, dest_path)
        blob.upload_from_file(fileobj, content_type=content_type)
        logger.info("File uploaded successfully to gs://%s/%s",
                    BUCKET, dest_path)
        return f"gs://{BUCKET}/{dest_path}"
    except Exception as e:
        logger.exception("Failed to upload file to GCS: %s", e)
        raise

# -----------------------------------------------------------------------------
# Download File
# -----------------------------------------------------------------------------


def download_to_path(gcs_uri: str, local_path: str):
    """
    Download a file from GCS (gs://bucket/path) to a local path.
    """
    try:
        assert gcs_uri.startswith("gs://"), "Expect gs:// URI"
        _, rest = gcs_uri.split("gs://", 1)
        bucket_name, blob_name = rest.split("/", 1)
        logger.info("Downloading from GCS: %s to local path: %s",
                    gcs_uri, local_path)
        bucket = client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)
        logger.info("Downloaded successfully to %s", local_path)
    except Exception as e:
        logger.exception("Failed to download file from GCS: %s", e)
        raise

# -----------------------------------------------------------------------------
# Generate Signed URL
# -----------------------------------------------------------------------------


def generate_signed_url(gcs_uri: str, minutes: int = 15) -> str:
    """
    Generate a signed URL for temporary access to a GCS object.
    """
    try:
        assert gcs_uri.startswith("gs://"), "Expect gs:// URI"
        _, rest = gcs_uri.split("gs://", 1)
        bucket_name, blob_name = rest.split("/", 1)
        logger.info(
            "Generating signed URL for: %s (expires in %d minutes)", gcs_uri, minutes)
        bucket = client().bucket(bucket_name)
        blob = bucket.blob(blob_name)
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=minutes), method="GET")
        logger.info("Signed URL generated successfully for %s", gcs_uri)
        return url
    except Exception as e:
        logger.exception("Failed to generate signed URL: %s", e)
        raise
