import os
import logging
from pathlib import Path
from google.cloud import storage
from common.config import settings

logger = logging.getLogger(__name__)

class GCSUtils:
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None and self.bucket_name:
            self._client = storage.Client(project=settings.GCP_PROJECT_ID)
        return self._client

    @property
    def bucket(self):
        if self._bucket is None and self.client:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def upload_file(self, local_path: str, remote_path: str) -> str:
        """
        Uploads a local file to GCS and returns the gs:// URI.
        If bucket is not configured, returns the local path as is (fallback for local dev).
        """
        if not self.bucket_name:
            logger.warning("GCS_BUCKET_NAME is not set. Falling back to local path.")
            return local_path

        if not self.bucket:
            logger.error(f"GCS Bucket '{self.bucket_name}' could not be initialized. Check project/credentials.")
            return local_path

        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
            gs_uri = f"gs://{self.bucket_name}/{remote_path}"
            logger.info(f"Successfully uploaded {local_path} to {gs_uri}")
            return gs_uri
        except Exception as e:
            logger.error(f"GCS Upload Error (Path: {remote_path}): {e}")
            # Do NOT return local path if we expect GCS to work in production
            # But for safety in current transition, we keep returning local_path
            return local_path

    async def download_file(self, remote_uri: str, local_path: str) -> str:
        """
        Downloads a file from GCS (if URI starts with gs://) to local_path.
        Returns the local path.
        """
        if not remote_uri.startswith("gs://") or not self.bucket:
            return remote_uri

        try:
            # Parse gs://bucket/path
            path_in_bucket = remote_uri.replace(f"gs://{self.bucket_name}/", "", 1)
            blob = self.bucket.blob(path_in_bucket)
            
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded {remote_uri} to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            return remote_uri

    def check_connectivity(self) -> bool:
        """
        Checks if the GCS bucket is accessible.
        """
        if not self.bucket:
            return False
        try:
            return self.bucket.exists()
        except Exception as e:
            logger.error(f"GCS connectivity check failed: {e}")
            return False

gcs_utils = GCSUtils()
