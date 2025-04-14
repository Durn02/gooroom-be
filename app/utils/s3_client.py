import boto3
from app.config.connection import (
    S3_REGION,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
)

# S3 클라이언트 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
)
