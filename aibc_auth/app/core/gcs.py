"""
Google Cloud Storage helper module for file uploads
"""
from google.cloud import storage
from google.oauth2 import service_account
from datetime import timedelta, datetime, timezone
from typing import Optional, BinaryIO
from pathlib import Path
import mimetypes
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class GCSManager:
    """Manages file uploads and downloads from Google Cloud Storage"""

    def __init__(self):
        """Initialize GCS client with credentials"""
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                credentials = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS
                )
                self.client = storage.Client(
                    credentials=credentials,
                    project=settings.GCS_PROJECT_ID
                )
            else:
                # Use default credentials (for Cloud Run)
                self.client = storage.Client(project=settings.GCS_PROJECT_ID)

            self.bucket_name = settings.GCS_BUCKET_NAME
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS Manager initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise

    def upload_file(
        self,
        file_content: BinaryIO,
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to GCS

        Args:
            file_content: File content as binary stream
            destination_path: Full path in GCS (e.g., pathways/image-generation/users/{user_id}/...)
            content_type: MIME type of the file

        Returns:
            Public GCS URL of the uploaded file
        """
        try:
            blob = self.bucket.blob(destination_path)

            # Guess content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(destination_path)
                content_type = content_type or 'application/octet-stream'

            # Upload file
            blob.upload_from_file(file_content, content_type=content_type)

            # Return public URL
            gcs_url = f"gs://{self.bucket_name}/{destination_path}"
            logger.info(f"File uploaded successfully to {gcs_url}")

            return gcs_url

        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise

    def generate_signed_url(
        self,
        blob_path: str,
        expiration_hours: int = 1
    ) -> str:
        """
        Generate a signed URL for secure file access

        Args:
            blob_path: Path to the file in GCS
            expiration_hours: URL expiration time in hours

        Returns:
            Signed URL string
        """
        try:
            blob = self.bucket.blob(blob_path)
            expiration = timedelta(hours=expiration_hours)

            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )

            logger.info(f"Generated signed URL for {blob_path} (expires in {expiration_hours}h)")
            return signed_url

        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise

    def delete_file(self, blob_path: str) -> bool:
        """
        Delete a file from GCS

        Args:
            blob_path: Path to the file in GCS

        Returns:
            True if successful
        """
        try:
            blob = self.bucket.blob(blob_path)
            blob.delete()
            logger.info(f"File deleted successfully from {blob_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file from GCS: {e}")
            raise

    def file_exists(self, blob_path: str) -> bool:
        """
        Check if a file exists in GCS

        Args:
            blob_path: Path to the file in GCS

        Returns:
            True if file exists
        """
        try:
            blob = self.bucket.blob(blob_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check file existence: {e}")
            return False

    def get_file_metadata(self, blob_path: str) -> Optional[dict]:
        """
        Get metadata for a file in GCS

        Args:
            blob_path: Path to the file in GCS

        Returns:
            Dictionary with file metadata
        """
        try:
            blob = self.bucket.blob(blob_path)
            blob.reload()

            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
                "md5_hash": blob.md5_hash
            }
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            return None


def validate_file_upload(
    filename: str,
    file_size: int,
    allowed_types: Optional[list],
    max_size_mb: int = 50
) -> tuple[bool, Optional[str]]:
    """
    Validate file upload parameters

    Args:
        filename: Name of the file
        file_size: Size of the file in bytes
        allowed_types: List of allowed MIME types (e.g., ['image/*', 'application/pdf'])
        max_size_mb: Maximum file size in megabytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb} MB"

    # Guess MIME type from filename
    mime_type, _ = mimetypes.guess_type(filename)

    if not mime_type:
        return False, "Could not determine file type"

    # Check if MIME type is allowed
    if allowed_types:
        is_allowed = False
        for allowed_type in allowed_types:
            if allowed_type.endswith('/*'):
                # Wildcard matching (e.g., 'image/*')
                category = allowed_type.split('/')[0]
                if mime_type.startswith(category + '/'):
                    is_allowed = True
                    break
            elif mime_type == allowed_type:
                # Exact match
                is_allowed = True
                break

        if not is_allowed:
            return False, f"File type '{mime_type}' is not allowed. Allowed types: {', '.join(allowed_types)}"

    return True, None


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename with timestamp prefix

    Args:
        original_filename: Original filename

    Returns:
        Unique filename with timestamp
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    safe_filename = "".join(c for c in original_filename if c.isalnum() or c in "._- ")
    return f"{timestamp}_{safe_filename}"


def build_gcs_path(
    pathway_id: str,
    user_id: str,
    resource_id: str,
    filename: str
) -> str:
    """
    Build the GCS path for a file upload

    Args:
        pathway_id: Pathway ID
        user_id: User ID
        resource_id: Resource ID
        filename: Filename (should be unique)

    Returns:
        Full GCS path
    """
    return f"pathways/{pathway_id}/users/{user_id}/resources/{resource_id}/{filename}"


# Singleton instance
_gcs_manager: Optional[GCSManager] = None


def get_gcs_manager() -> GCSManager:
    """Get or create GCS manager singleton"""
    global _gcs_manager
    if _gcs_manager is None:
        _gcs_manager = GCSManager()
    return _gcs_manager
