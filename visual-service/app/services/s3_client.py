"""S3 client service for file storage operations."""
import aioboto3
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime
from pathlib import Path
from app.config import settings
from app.utils.logger import logger


class S3Client:
    """Async S3 client for MinIO/AWS S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self.bucket_name = settings.S3_BUCKET
        self.endpoint_url = settings.S3_ENDPOINT
        self.use_ssl = settings.S3_USE_SSL

    async def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: str = "image/png",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload file to S3.

        Args:
            file_path: Local file path to upload
            object_key: S3 object key (path in bucket)
            content_type: MIME type of the file
            metadata: Additional metadata

        Returns:
            Public URL of uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                extra_args = {
                    "ContentType": content_type,
                }
                if metadata:
                    extra_args["Metadata"] = metadata

                await s3.upload_file(
                    file_path,
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args,
                )

                url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
                logger.info(f"File uploaded successfully: {object_key}")
                return url

        except Exception as e:
            logger.error(f"Failed to upload file {object_key}: {str(e)}")
            raise

    async def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: str = "image/png",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload file object to S3.

        Args:
            file_obj: File-like object to upload
            object_key: S3 object key
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            Public URL of uploaded file
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                extra_args = {
                    "ContentType": content_type,
                }
                if metadata:
                    extra_args["Metadata"] = metadata

                await s3.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    object_key,
                    ExtraArgs=extra_args,
                )

                url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
                logger.info(f"File object uploaded successfully: {object_key}")
                return url

        except Exception as e:
            logger.error(f"Failed to upload file object {object_key}: {str(e)}")
            raise

    async def get_file_info(self, object_key: str) -> Dict[str, Any]:
        """Get file metadata from S3.

        Args:
            object_key: S3 object key

        Returns:
            File metadata dict

        Raises:
            Exception: If file not found or operation fails
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                response = await s3.head_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                )

                return {
                    "size": response["ContentLength"],
                    "content_type": response.get("ContentType", "unknown"),
                    "last_modified": response["LastModified"].isoformat(),
                    "metadata": response.get("Metadata", {}),
                }

        except Exception as e:
            logger.error(f"Failed to get file info for {object_key}: {str(e)}")
            raise

    async def delete_file(self, object_key: str) -> bool:
        """Delete file from S3.

        Args:
            object_key: S3 object key

        Returns:
            True if deleted successfully

        Raises:
            Exception: If deletion fails
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                )

                logger.info(f"File deleted successfully: {object_key}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete file {object_key}: {str(e)}")
            raise

    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
    ) -> str:
        """Generate presigned URL for temporary access.

        Args:
            object_key: S3 object key
            expiration: URL expiration in seconds (default: 1 hour)

        Returns:
            Presigned URL

        Raises:
            Exception: If generation fails
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": object_key,
                    },
                    ExpiresIn=expiration,
                )

                logger.info(f"Presigned URL generated for: {object_key}")
                return url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {object_key}: {str(e)}")
            raise

    async def check_health(self) -> bool:
        """Check S3 connection health.

        Returns:
            True if connection is healthy
        """
        try:
            async with self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
                return True

        except Exception as e:
            logger.error(f"S3 health check failed: {str(e)}")
            return False


s3_client = S3Client()
