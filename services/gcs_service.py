"""
Google Cloud Storage service for Team Synapse.
Handles file uploads, downloads, and cleanup.
"""
import os
import time
from typing import Optional
from google.cloud import storage
from google.api_core import exceptions

from config import config
from utils import setup_logger


logger = setup_logger(__name__, config.app.log_level)


class GCSService:
    """Service for managing Google Cloud Storage operations."""
    
    def __init__(self):
        """Initialize GCS client."""
        try:
            self.client = storage.Client()
            self.bucket_name = config.google_cloud.gcs_bucket_name
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS Service initialized with bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise
    
    def upload_file(self, local_file_path: str, folder: str = "ingestion") -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            local_file_path: Path to the local file
            folder: Folder in the bucket to upload to
        
        Returns:
            GCS URI (gs://bucket/path)
        
        Raises:
            Exception: If upload fails
        """
        try:
            # Create unique blob name with timestamp
            filename = os.path.basename(local_file_path)
            timestamp = int(time.time())
            blob_name = f"{folder}/{timestamp}_{filename}"
            
            blob = self.bucket.blob(blob_name)
            
            # Upload with progress logging
            logger.info(f"Uploading {filename} to GCS...")
            blob.upload_from_filename(local_file_path)
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.info(f"Upload successful: {gcs_uri}")
            
            return gcs_uri
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"GCS API error during upload: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise
    
    def delete_file(self, gcs_uri: str) -> bool:
        """
        Delete a file from Google Cloud Storage.
        
        Args:
            gcs_uri: Full GCS URI (gs://bucket/path)
        
        Returns:
            True if deletion successful, False otherwise
        """
        if not gcs_uri or not gcs_uri.startswith("gs://"):
            logger.warning(f"Invalid GCS URI: {gcs_uri}")
            return False
        
        try:
            # Parse URI
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                logger.warning(f"Malformed GCS URI: {gcs_uri}")
                return False
            
            bucket_name, blob_name = parts
            
            # Delete blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted GCS file: {gcs_uri}")
                return True
            else:
                logger.warning(f"GCS file not found: {gcs_uri}")
                return False
                
        except exceptions.GoogleAPIError as e:
            logger.error(f"GCS API error during deletion: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {e}")
            return False
    
    def file_exists(self, gcs_uri: str) -> bool:
        """
        Check if a file exists in GCS.
        
        Args:
            gcs_uri: Full GCS URI (gs://bucket/path)
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                return False
            
            bucket_name, blob_name = parts
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
    
    def cleanup_old_files(self, folder: str = "ingestion", age_hours: int = 24) -> int:
        """
        Clean up files older than specified age.
        
        Args:
            folder: Folder to clean up
            age_hours: Delete files older than this many hours
        
        Returns:
            Number of files deleted
        """
        try:
            blobs = self.client.list_blobs(self.bucket_name, prefix=f"{folder}/")
            current_time = time.time()
            deleted_count = 0
            
            for blob in blobs:
                # Check if file is old enough to delete
                if blob.time_created:
                    age_seconds = current_time - blob.time_created.timestamp()
                    if age_seconds > (age_hours * 3600):
                        blob.delete()
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files from {folder}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0


# Global service instance
gcs_service = GCSService()