import json
import time
import uuid
import redis
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("status_store")

STATUS_PREFIX = "job:"

class StatusStore:
    def __init__(self, url: str | None = None):
        """Initialize Redis connection for job status tracking."""
        redis_url = url or os.environ.get("REDIS_URL")
        logger.info("Initializing Redis connection (URL=%s)", redis_url)
        try:
            self.r = redis.Redis.from_url(redis_url)
            # Test connection
            self.r.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.exception("Failed to connect to Redis: %s", e)
            raise

    def new_job(self, filename: str) -> str:
        """Create a new job record and return its ID."""
        job_id = str(uuid.uuid4())
        data = {
            "id": job_id,
            "filename": filename,
            "status": "RECEIVED",
            "progress": 10,
            "stage": "Upload requested",
            "created_at": int(time.time()),
        }

        try:
            self.r.hset(STATUS_PREFIX + job_id, mapping=data)
            logger.info(
                "[Job %s] Created new job record: filename='%s', status='RECEIVED'",
                job_id,
                filename,
            )
        except Exception as e:
            logger.exception(
                "[Job %s] Failed to create job record: %s", job_id, e)
            raise

        return job_id

    def update(self, job_id: str, **fields):
        """Update an existing job record with given fields."""
        try:
            current_data = self.get(job_id)
            if not current_data:
                logger.warning(
                    "[Job %s] No existing record found to update.", job_id)
                return

            if "progress" in fields:
                # keep progress monotonic
                current_progress = int(current_data.get("progress", 0))
                new_progress = int(fields["progress"])
                fields["progress"] = max(new_progress, current_progress)

            # Convert all values to strings for Redis
            fields_str = {k: str(v) for k, v in fields.items()}
            self.r.hset(STATUS_PREFIX + job_id, mapping=fields_str)

            logger.info(
                "[Job %s] Updated fields: %s",
                job_id,
                json.dumps(fields_str, ensure_ascii=False),
            )
        except Exception as e:
            logger.exception("[Job %s] Failed to update status: %s", job_id, e)
            raise

    def get(self, job_id: str) -> dict:
        """Retrieve the job record from Redis as a dictionary."""
        try:
            raw = self.r.hgetall(STATUS_PREFIX + job_id)
            if not raw:
                logger.debug("[Job %s] No status found in Redis.", job_id)
                return {}

            data = {k.decode(): v.decode() for k, v in raw.items()}
            logger.debug("[Job %s] Retrieved status: %s",
                         job_id, json.dumps(data))
            return data
        except Exception as e:
            logger.exception("[Job %s] Failed to fetch status: %s", job_id, e)
            return {}