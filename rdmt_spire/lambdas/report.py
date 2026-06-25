import logging
import os
from datetime import datetime

import boto3
import duckdb

from ..constants.codes import StatusCodes
from ..constants.lambdas import (
    AWS_DBS,
    AWS_PARAMETER_PATH,
    AWS_S3_BUCKETS,
    AWS_SNS_TOPICS,
    DB_NAME,
    DB_SECRET_NAME,
    PARQUET_FILE_BUCKET,
    REPORTING_TOPIC,
)
from ..db_tables.sci_tables import L2ScienceResultsTable
from ..utilities.aws_utils import fetch_parameters_from_path
from ..utilities.db_utils import connect_to_db

logger = logging.getLogger()
logger.setLevel(logging.INFO)

tab_str = "    "

def report_function():
    """
    Orchestrates the extraction, transformation, and reporting of RDMT file 
    metadata, metrics and evaluations.

    This function connects to a MySQL database via DuckDB, identifies new 
    records ready for reporting based on monitor status, updates their report 
    timestamps, exports the combined metadata and results to a partitioned S3 
    Parquet dataset, and finally sends a summary notification via AWS SNS.

    The process follows an ELT (Extract, Load, Transform) pattern leveraging 
    DuckDB's in-memory processing and S3 connectivity.

    Parameters
    ----------
    None
        The function retrieves necessary connection details and configurations 
        from environment variables and `connect_to_db` utilities.

    Returns
    -------
    dict
        A dictionary containing the execution status and a summary message.
        Example: ``{'statusCode': 200, 'body': [{'_message': '...'}]}``.
    """
    params = fetch_parameters_from_path(AWS_PARAMETER_PATH, expected_parameters=AWS_S3_BUCKETS + AWS_SNS_TOPICS + AWS_DBS)

    conn = None
    try:
        logger.info('Getting SQL URL')
        sql_url = connect_to_db(database_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME]).url

        # initialize duckdb local database
        logger.info('Connecting to duckdb')
        conn = duckdb.connect(database=':memory:')
        duckdb_extension_path = os.environ.get('DUCKDB_EXTENSIONS_PATH', '/duckdb_extensions')
        conn.execute(f"SET extension_directory = '{duckdb_extension_path}';")

        # Load the extensions pre-baked into your Docker image
        # 'mysql': To connect to MySQL; 'aws' & 'httpfs': To stream directly to S3
        logger.info('Loading duckdb modules')
        conn.execute("LOAD mysql;")# TODO: LOAD aws; LOAD httpfs;")
        
        # 2. Create a secret using the 'credential_chain' provider
        # This tells DuckDB to automatically find credentials using AWS SDK mechanisms
        logger.info('Creating duckdb secrets')
        conn.execute("CREATE SECRET (TYPE s3, PROVIDER credential_chain);")

        # --- 3. LINKING THE DATABASE ---
        # Construct a DuckDB-specific connection string from the SQLAlchemy object
        create_secret_sql = f"""
            CREATE OR REPLACE TEMPORARY SECRET db_secret (
                TYPE mysql,
                HOST '{sql_url.host}',
                DATABASE '{sql_url.database}',
                USER '{sql_url.username}',
                PASSWORD '{sql_url.password}'
            );
            """
        conn.sql(create_secret_sql)

        # 'ATTACH' creates a virtual link. It does NOT download the data yet.
        # To DuckDB, the remote MySQL database now behaves like a local schema.
        logger.info('Attaching external database to duckdb')
        conn.sql("ATTACH '' AS rdmt_db (TYPE mysql, SECRET 'db_secret');")
        
        # Switch to using rdmt_db server as default to allow SQLAlchemy to make SQL strings
        conn.sql("USE rdmt_db;")

        # Generate the report datetime and set the value for all columns to be reported (e.g. all rows where file reported date is not populated but all "_status" columns are -1 or 1 (indicating all monitors that needed to run have done so successfully))
        report_time = datetime.now().replace(microsecond=0)
        update_report_time_str = """
            UPDATE l2_science_meta
            SET monitor_end_datetime = $1
            WHERE astrometry_status IN (-1, 1) AND noise_1f_status IN (-1, 1)
            AND monitor_end_datetime IS NULL 
        """
        update_report_result = conn.execute(update_report_time_str, (report_time,))
        num_reported_rows = update_report_result.fetchall()[0][0]
        logger.info(f"Number of reported rows: {num_reported_rows}")

        if num_reported_rows > 0:
            # Package metadata and results data into Parquet dataset
            s3_parquet_bucket_path = f"s3://{params[PARQUET_FILE_BUCKET]}/"

            # Check if we should create the parquet structure or append to it
            s3_client = boto3.client('s3')
            response = s3_client.list_objects_v2(Bucket=params[PARQUET_FILE_BUCKET], MaxKeys=1)
            # If there are already files in the bucket
            if 'Contents' in response:
                parquet_command = ", APPEND"
                logger.info('Parquet dataset exists. Appending new rows.')
            else:
                parquet_command = ""
                logger.info('Parquet dataset does not exist. Creating new dataset.')

            # TODO: We might want to sort the exported Parquet file by visit id or obs id or program to speed up queries
            parquet_file_pattern = "rdmt_db_{uuid}" # define prefix followed by unique ID, intentionally not an f-string
            parquet_export_str = f"""
                COPY (
                    SELECT 
                        M.*,
                        R.* EXCLUDE(filename, reprocess_number),
                        year(M.exp_start_datetime) AS obs_year_part, 
                        month(M.exp_start_datetime) AS obs_month_part 
                    FROM l2_science_meta AS m
                    JOIN l2_science_results AS R
                    ON M.filename = R.filename AND M.reprocess_number = R.reprocess_number
                    WHERE M.monitor_end_datetime = $1
                ) 
                TO '{s3_parquet_bucket_path}' 
                (FORMAT PARQUET, PARTITION_BY (obs_year_part, obs_month_part) {parquet_command}, FILENAME_PATTERN '{parquet_file_pattern}');
            """
            conn.execute(parquet_export_str, (report_time,))
            logger.info("Saved parquet file to dataset.")

            logger.info("Generating report message string.")
            report_message = generate_report_message(conn, s3_parquet_bucket_path, report_time)

            # Send out an SNS report of all
            logger.info("Sending SNS Email notification.")
            sns = boto3.client('sns')
            report_topic = sns.create_topic(Name=params[REPORTING_TOPIC])
            try:
                response = sns.publish(
                    TopicArn=report_topic['TopicArn'],
                    Message=report_message,
                    Subject=f"RDMT Spire Report for {report_time.strftime('%Y-%m-%d')}",
                )
                logger.info('Successfully posted report to topic.')
            except Exception as e:
                logger.error(f'{e}')
                raise e

        else:
            logger.info('No new rows to report.')

            return {'statusCode': StatusCodes.SUCCESS,
                    'body': [{'message':'report_function: No new rows to report.'}]}

    except Exception as e:
        logger.error(f"{e}")
        if conn is not None:
            databases = conn.sql("SHOW DATABASES").fetchall()
            if ('rdmt_db',) in databases:
                conn.execute("DETACH rdmt_db;")
            conn.close()
        raise e

    logger.info("Successfully finished reporting lambda.")
    return {'statusCode': StatusCodes.SUCCESS,
                'body': [{'_message':'Successfully completed report_function.'}]}

def generate_report_message(duckdb_connection, s3_parquet_bucket, report_generation_time):
    """
    Orchestrate the creation of a RDMT SPIRE report message string.

    This function acts as the primary entry point for report generation. It 
    constructs the S3 file path, calls sub-functions to identify failed 
    evaluations and monitored file summaries, and wraps the results in a 
    standardized header and layout.

    Parameters
    ----------
    duckdb_connection : duckdb.DuckDBPyConnection
        An active DuckDB connection object capable of executing SQL queries.
    s3_parquet_bucket : str
        The base S3 bucket path (e.g., 's3://my-data-bucket/'). The function 
        appends wildcards to search for nested Parquet files.
    report_generation_time : str or datetime
        The specific timestamp used to filter the `monitor_end_datetime` 
        column in the dataset.

    Returns
    -------
    message : str
        The complete, formatted SPIRE report containing a timestamped header, 
        a list of failed evaluations, and a hierarchical summary of 
        monitored files.
    
    """
    s3_parquet_file_path = os.path.join(s3_parquet_bucket, "*/*/*.parquet")
    # Query the same subset from the results table and extract evaluations that failed

    eval_str = get_failed_evaluations(duckdb_connection, s3_parquet_file_path, report_generation_time)
    info_str = get_monitored_files(duckdb_connection, s3_parquet_file_path, report_generation_time)

    hline = "-"*40
    message = f"""
    ROMAN DATA MONITORING TOOL SPIRE REPORT 

    Generated: {report_generation_time.strftime('%Y-%m-%d %H:%M:%S')}
    {hline}
    
    FAILED EVALUATIONS:
    {hline}
    {eval_str}
    
    MONITORED FILES SUMMARY:
    {hline}
    {info_str}
    
    

    """

    return message

def get_failed_evaluations(duckdb_connection, s3_parquet_file_path, report_generation_time):
    """
    Identify and format metric evaluations that failed (False) in a report.

    This function dynamically constructs a DuckDB SQL query to unpivot metric 
    and evaluation columns from a Parquet dataset. It filters for rows where 
    the evaluation result is False and returns a formatted string of the 
    failures.

    Parameters
    ----------
    duckdb_connection : duckdb.DuckDBPyConnection
        An active DuckDB connection object capable of executing SQL queries.
    s3_parquet_file_path : str
        The S3 URI or path to the Parquet files (e.g., 's3://bucket/data/').
        Must support Hive-style partitioning.
    report_generation_time : str or datetime
        The specific timestamp used to filter the `monitor_end_datetime` 
        column in the dataset.

    Returns
    -------
    eval_str : str
        A formatted string listing failed evaluations. Each entry includes:
        - Filename
        - Reprocess number
        - Name of the failed metric
        - Value of the metric (formatted to 4 decimal places)
    """
    metric_eval_pairs = L2ScienceResultsTable().get_metric_eval_pairs()
    unpivot_metric_list = ", ".join([f"({m}, {e}) AS '{m}'" for m, e in metric_eval_pairs])

    eval_check_str = f"""
        SELECT
            filename,
            reprocess_number,
            metric_name,
            metric_value,
            evaluation
        FROM (
            UNPIVOT (
                SELECT * 
                FROM read_parquet('{s3_parquet_file_path}', hive_partitioning=true)
                WHERE 
                    obs_year_part = YEAR(exp_start_datetime)
                    AND obs_month_part = MONTH(exp_start_datetime)
                    AND monitor_end_datetime = $1
            )
            ON {unpivot_metric_list}
            INTO
                NAME metric_name
                VALUE (metric_value, evaluation)
        )
        WHERE evaluation = False;
    """
    eval_result = duckdb_connection.execute(eval_check_str, (report_generation_time,)).fetchall()

    eval_str = ""
    for row in eval_result:
        filename, rep_num, metric_name, metric_value, _ = row
        eval_str += f"{filename} (rep # {rep_num})  >>  {metric_name} = {metric_value:.4f}\n" + tab_str

    return eval_str 

def get_monitored_files(duckdb_connection, s3_parquet_file_path, report_generation_time):
    """
    Query Parquet files from S3 and format a file summary report string.

    This function executes a DuckDB query against S3-hosted Parquet files to
    aggregate observation data (grouped by day, program, and observation ID).
    It identifies missing detectors if the count is not exactly 18 and formats
     the results into a hierarchical string structure.

    Parameters
    ----------
    duckdb_connection : duckdb.DuckDBPyConnection
        An active DuckDB connection object capable of executing SQL queries.
    s3_parquet_file_path : str
        The S3 URI or path to the Parquet files (e.g., 's3://bucket/data/').
        Must support Hive-style partitioning.
    report_generation_time : str or datetime
        The specific timestamp used to filter the `monitor_end_datetime` 
        column in the dataset.

    Returns
    -------
    info_str : str
        A formatted multi-line string reporting observations organized by:
        - Observation Day
            - Program Number
                - Observation ID and Reprocess Number
        Includes an "ALERT" tag for any observation with fewer than 18 detectors.
    """
    report_info_str = f"""
        SELECT 
            CAST(exp_start_datetime AS DATE) AS obs_day, 
            reprocess_number,
            program_number,
            observation_id,
            list(detector) as detector_list,
            COUNT(detector) as detector_count,
        FROM read_parquet('{s3_parquet_file_path}', hive_partitioning=true)
        WHERE 
            obs_year_part = YEAR(exp_start_datetime)
            AND obs_month_part = MONTH(exp_start_datetime)
            AND monitor_end_datetime = $1
        GROUP BY obs_day, program_number, reprocess_number, observation_id
        ORDER BY obs_day ASC, program_number ASC, reprocess_number ASC, observation_id ASC;
    """
    info_result = duckdb_connection.execute(report_info_str, (report_generation_time,)).fetchall()

    info_str = ""
    print_day = None
    print_program_num = None
    for row in info_result:
        day, rep_num, program_num, obs_id, detectors, det_count = row
        if day != print_day:
            print_day = day
            print_program_num = program_num
            if len(info_str) == 0:
                info_str += f"{day}:\n"
            else:
                info_str += tab_str + f"{day}:\n"
            info_str += 2*tab_str + f"Program {program_num}:\n"
        elif program_num != print_program_num:
            print_program_num = program_num
            info_str += 2*tab_str + f"Program {program_num}:\n"
        info_str += 3*tab_str + f"{obs_id} (rep # {rep_num})"
        if det_count != 18:
            detectors.sort()
            det_list = [det.upper().removeprefix('WFI').lstrip('0') for det in detectors]
            info_str += f"  >>  ALERT: Only received detectors {" ,".join(det_list)}\n"
        else:
            info_str += "\n"

    return info_str