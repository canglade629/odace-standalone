"""GCS operations utilities."""
import io
from typing import List, BinaryIO, Optional
from google.cloud import storage
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class GCSOperations:
    """Helper class for Google Cloud Storage operations."""
    
    def __init__(self):
        """Initialize GCS client."""
        self.settings = get_settings()
        self.client = storage.Client(project=self.settings.gcp_project_id)
        self.bucket = self.client.bucket(self.settings.gcs_bucket)
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List files in a GCS path.
        
        Args:
            prefix: Path prefix to list
            
        Returns:
            List of file paths
        """
        blobs = self.client.list_blobs(self.settings.gcs_bucket, prefix=prefix)
        files = []
        for blob in blobs:
            # Skip directories (blobs ending with /)
            if not blob.name.endswith('/'):
                files.append(f"gs://{self.settings.gcs_bucket}/{blob.name}")
        return files
    
    def download_file(self, gcs_path: str) -> bytes:
        """
        Download a file from GCS.
        
        Args:
            gcs_path: Full GCS path (gs://bucket/path/to/file)
            
        Returns:
            File contents as bytes
        """
        # Remove gs://bucket/ prefix
        path = gcs_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        blob = self.bucket.blob(path)
        return blob.download_as_bytes()
    
    def download_to_stream(self, gcs_path: str) -> io.BytesIO:
        """
        Download a file to a BytesIO stream.
        
        Args:
            gcs_path: Full GCS path
            
        Returns:
            BytesIO stream with file contents
        """
        content = self.download_file(gcs_path)
        return io.BytesIO(content)
    
    def upload_file(self, local_file: BinaryIO, gcs_path: str) -> str:
        """
        Upload a file to GCS.
        
        Args:
            local_file: File object to upload
            gcs_path: Destination GCS path (gs://bucket/path/to/file)
            
        Returns:
            Full GCS path of uploaded file
        """
        # Remove gs://bucket/ prefix
        path = gcs_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        blob = self.bucket.blob(path)
        
        # Read file content
        local_file.seek(0)
        content = local_file.read()
        
        blob.upload_from_string(content)
        logger.info(f"Uploaded file to {gcs_path}")
        return gcs_path
    
    def upload_from_string(self, content: str, gcs_path: str) -> str:
        """
        Upload string content to GCS.
        
        Args:
            content: String content to upload
            gcs_path: Destination GCS path
            
        Returns:
            Full GCS path of uploaded file
        """
        path = gcs_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        blob = self.bucket.blob(path)
        blob.upload_from_string(content)
        logger.info(f"Uploaded content to {gcs_path}")
        return gcs_path
    
    def file_exists(self, gcs_path: str) -> bool:
        """
        Check if a file exists in GCS.
        
        Args:
            gcs_path: Full GCS path
            
        Returns:
            True if file exists, False otherwise
        """
        path = gcs_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        blob = self.bucket.blob(path)
        return blob.exists()
    
    def get_file_info(self, gcs_path: str) -> dict:
        """
        Get file metadata.
        
        Args:
            gcs_path: Full GCS path
            
        Returns:
            Dictionary with file metadata
        """
        path = gcs_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        blob = self.bucket.blob(path)
        blob.reload()
        
        return {
            "name": blob.name,
            "size": blob.size,
            "content_type": blob.content_type,
            "updated": blob.updated,
            "md5_hash": blob.md5_hash
        }


# Global instance
_gcs_ops: Optional[GCSOperations] = None


def get_gcs_operations() -> GCSOperations:
    """Get or create global GCS operations instance."""
    global _gcs_ops
    if _gcs_ops is None:
        _gcs_ops = GCSOperations()
    return _gcs_ops

