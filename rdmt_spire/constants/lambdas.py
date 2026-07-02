import os
from enum import StrEnum

# AWS Parameter store path and parameter names
prefix = os.getenv("PROFILE_NAME_PREFIX", "rdmt")
AWS_PARAMETER_PATH = f"/{prefix}/config/"

# SQS queue parameter names
NOISE_1F_MONITOR_QUEUE = "noise_1f_monitor_queue"
ASTROMETRY_MONITOR_QUEUE = "astrometry_monitor_queue"

AWS_MONITOR_QUEUES = [
    NOISE_1F_MONITOR_QUEUE,
    ASTROMETRY_MONITOR_QUEUE,
]

# SNS topic parameter names
REPORTING_TOPIC = "reporting_topic"

AWS_SNS_TOPICS = [
    REPORTING_TOPIC,
]

# S3 bucket parameter names
PARQUET_FILE_BUCKET = "parquet_file_bucket"
ALEMBIC_VERSIONS_BUCKET = "alembic_versions_bucket"
ASTROMETRY_MONITOR_DATA_BUCKET = "astrometry_monitor_data_bucket"

AWS_S3_BUCKETS = [
    PARQUET_FILE_BUCKET,
    ALEMBIC_VERSIONS_BUCKET,
    ASTROMETRY_MONITOR_DATA_BUCKET,
]

# Database parameter names
DB_NAME = "db_name"
DB_SECRET_NAME = "db_secret_name"

AWS_DBS = [
    DB_NAME,
    DB_SECRET_NAME,
]


class FunctionTypes(StrEnum):
    MONITOR = "monitor"
    METADATA_CHECK = "meta_check"
    REPORT_GEN = "report"

class MessageKeys(StrEnum):
    # The following keys are defined by DMD in their Archiving SNS Topic notifications
    ARCHIVE_BUCKET = "archiveBucket"
    ARCHIVE_OBJECT_KEY = "archiveObjectKey"
    FILE_TYPE = "fileType"
    FILE_CREATION_TIMESTAMP = "fileCreationTimestamp"
    FILENAME = "filename"
    REPROCESSING_STATE = "reprocessingState"

    # The following keys are only used within Spire itself
    FUNCTION_TYPE = "function_type"
    MONITOR_NAME = "monitor_name"
    REPROCESS_NUMBER = "reprocess_number"

    METADATA_CHECK_TYPE = 'metadata_check_type'
