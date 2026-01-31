import os
import logging
from pathlib import Path
from google.cloud import storage
from common.config import settings

logger = logging.getLogger(__name__)

class GCSUtils:
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.client = storage.Client() if self.bucket_name else None
        self.bucket = self.client.bucket(self.bucket_name) if self.client else None

    def upload_file(self, local_path: str, remote_path: str) -> str:
        """
        Uploads a local file to GCS and returns the gs:// URI.
        If bucket is not configured, returns the local path as is (fallback for local dev).
        """
        if not self.bucket:
            logger.warning("GCS_BUCKET_NAME not configured. Using local path.")
            return local_path

        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(local_path)
            gs_uri = f"gs://{self.bucket_name}/{remote_path}"
            logger.info(f"Uploaded {local_path} to {gs_uri}")
            return gs_uri
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return local_path

    def download_file(self, remote_uri: str, local_path: str) -> str:
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

gcs_utils = GCSUtils()
