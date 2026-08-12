from datetime import timedelta, datetime
import json
import logging

import boto3
from sqlalchemy import case, inspect as sa_inspect, or_, and_, tuple_, select, update
from sqlalchemy.orm import Session

from ..constants.codes import StatusCodes
from ..constants.lambdas import (
    ASTROMETRY_MONITOR_QUEUE,
    AWS_DBS,
    AWS_MONITOR_QUEUES,
    AWS_PARAMETER_PATH,
    DB_NAME,
    DB_SECRET_NAME,
    FunctionTypes,
    MessageKeys,
)
from ..db_tables.sci_tables import L2ScienceMetaTable
from ..utilities.aws_utils import fetch_parameters_from_path, get_sqs_url
from ..utilities.db_utils import connect_to_db

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def metadata_check_function(message_dict, aws_account_id):
    """
    Run a metadata check and enqueue monitor messages to SQS based on the
    requested check type (currently supports ``'astrometry'`` only).

    This function inspects metadata records that require monitoring, identified
    via database queries, and sends a message per record to the appropriate SQS
    queue. It returns an API-like response indicating success or a
    not-yet-implemented status for unsupported check types.

    Parameters
    ----------
    message_dict : dict
        Input payload containing routing/configuration fields. Must include
        ``MessageKeys.METADATA_CHECK_TYPE`` with a string value identifying the
        check type to run (e.g., ``'astrometry'``).
    aws_account_id : str
        AWS account ID used to resolve SQS queue URLs.

    Returns
    -------
    dict
        A response object with:
        - ``'statusCode'`` : int
        - ``'body'`` : list of dict
            A list with a message on success or an error message when not implemented.

    """

    params = fetch_parameters_from_path(AWS_PARAMETER_PATH, expected_parameters=AWS_MONITOR_QUEUES + AWS_DBS)

    all_status_columns = [
        column.key for column in sa_inspect(L2ScienceMetaTable).columns if column.key.endswith("_status")
    ]

    metadata_check_status_columns = [
        "astrometry_status",
        "test_reject_status",  # purely for testing!
    ]

    logger.info(f"Running Metadata check for columns: {', '.join(metadata_check_status_columns)}")

    logger.info('Connecting to the database...')
    sql_engine = connect_to_db(database_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME])

    # Query the database for all *_status columns in metadata_check_status_columns that are set to -2 which indicates they may need to be run. Return all rows. If there are other _status columns that are set to -2, raise a ValueError.
    with Session(sql_engine) as session:
        logger.info("Querying database for new rows to check ...")
        all_min2_statuses = or_(
            *[getattr(L2ScienceMetaTable, col) == -2 for col in all_status_columns]
        )
        ids_and_status_columns = [
            L2ScienceMetaTable.filename,
            L2ScienceMetaTable.reprocess_number,
            L2ScienceMetaTable.exp_start_datetime,
            *[getattr(L2ScienceMetaTable, col) for col in all_status_columns],
        ]
        pk_rows = session.execute(
            select(*ids_and_status_columns).where(all_min2_statuses)
            .order_by(L2ScienceMetaTable.exp_start_datetime.asc())
        ).all()

        non_metadata_check_status_columns = [
            col for col in all_status_columns if col not in metadata_check_status_columns
        ]
        if non_metadata_check_status_columns and any(
            getattr(row, col) == -2 for row in pk_rows for col in non_metadata_check_status_columns
        ):
            bad_columns = []
            for row in pk_rows:
                for col in non_metadata_check_status_columns:
                    if getattr(row, col) == -2:
                        logger.error(f"Row with filename={row.filename}, reprocess_number={row.reprocess_number} has {col} == -2, which is not supported for metadata checks.")
                        bad_columns.append(col)
            raise ValueError(
                "Found rows with -2 in unsupported status columns: "
                f"{', '.join(set(bad_columns))}"
            )

        if not pk_rows:
            logger.info("No rows found with any *_status == -2. No messages will be sent to SQS.")
            return {
                "statusCode": StatusCodes.SUCCESS,
                "body": [{"message": "No rows found with any *_status == -2. No messages sent to SQS."}],
            }
        
        logger.info(f"Found {len(pk_rows)} rows with any *_status == -2.")

        logger.info("Defining selection rules for metadata checks ...")
        # Define the selection rules for each metadata check type. Each rule consists of a SQLAlchemy query
        rules = {}
        # astrometry should run every hour, so query to find last time it ran and find any occurrences that need to be run.
        logger.info("Defining selection rule for astrometry ...")
        astrometry_rule = every_other_astrometry_rule(pk_rows)
        # TODO: test once we have more data spread across time
        #astrometry_rule = time_based_astrometry_rule(session, pk_rows)
        rules['astrometry_status'] = astrometry_rule

        logger.info("Defining selection rule for test_reject ...")
        # test_reject_status is purely for testing and should run on every file that has it set to -2
        test_reject_rule = [(L2ScienceMetaTable.test_reject_status == -2, -1)]
        rules['test_reject_status'] = test_reject_rule

        # Validate the rules to ensure they are in the correct format (tuple or list of tuples)
        logger.info("Validating selection rules and building sql statement ...")
        rule_statements = {}
        for col, rule in rules.items():
            if isinstance(rule, list) and all(isinstance(r, tuple) and len(r) == 2 for r in rule):
                rule_statements[col] = case(*rule, else_=-1)
            else:
                raise ValueError(f"Invalid rule format for {col}: {rule}. Must be a tuple or list of tuples.")
            
            
        # Update the rows that match the selection rules to 0 and set all other rows to -1
        logger.info("Updating rows in the database based on selection rules ...")
        pk_values = [(row.filename, row.reprocess_number) for row in pk_rows]

        stmt = (
            update(L2ScienceMetaTable)
            .where(
                tuple_(
                    L2ScienceMetaTable.filename,
                    L2ScienceMetaTable.reprocess_number,
                ).in_(pk_values)
            )
            .values(rule_statements)
            .execution_options(synchronize_session=False)
        )

        session.execute(stmt)
        session.commit()


        # Loop over rows that have had a _status set to 0 and send a message to the appropriate SQS queue for each row.
        logger.info("Querying database for rows that have been updated to *_status == 0 ...")
        updated_rows = session.execute(
            select(L2ScienceMetaTable).where(
                and_(
                    tuple_(
                        L2ScienceMetaTable.filename,
                        L2ScienceMetaTable.reprocess_number,
                    ).in_(pk_values),
                    or_(*[getattr(L2ScienceMetaTable, col) == 0 for col in metadata_check_status_columns])
                )
            )
        ).scalars().all()

    if not updated_rows:
        return {
            "statusCode": StatusCodes.SUCCESS,
            "body": [{"message": "No rows found with any *_status == 0 after update. No messages sent to SQS."}],
        }
    
    logger.info(f"Found {len(updated_rows)} rows with *_status == 0 after update. Sending messages to SQS.")
    sqs = boto3.client("sqs", region_name='us-east-1')
    astrometry_rows = [row for row in updated_rows if row.astrometry_status == 0]
    if astrometry_rows:
        astrometry_queue = get_sqs_url(
            params[ASTROMETRY_MONITOR_QUEUE], 
            account_id=aws_account_id
        )
        for row in astrometry_rows:
            monitor_dict = generate_message_dict_from_metadata_table(row, 'astrometry')
            try:
                # Send the message to the queue associated with this key.
                response = sqs.send_message(
                    QueueUrl=astrometry_queue,
                    MessageBody=json.dumps(monitor_dict)
                )
                logger.info(f'Message sent for astrometry. Response: {response}')
            except Exception as e:
                logger.error(f"Failed in sending message: {e}")
                # TODO: how do we want to handle this error correctly?
                raise e

    test_reject_rows = [row for row in updated_rows if row.test_reject_status == 0]
    if test_reject_rows:
        raise NotImplementedError("test_reject_status is purely for testing and should not be used in production.")

    logger.info('Successfully sent all messages. Metadata check complete,')

    return {'statusCode': StatusCodes.SUCCESS,
                'body': [{'message':'metadata_check_function ran successfully.'}]} 

def every_other_astrometry_rule(pk_rows):
    """
    Determine which rows should have astrometry monitoring run based on a rule that selects every other row.

    Parameters
    ----------
    pk_rows : list of tuples
        A list of tuples containing at least (filename, reprocess_number, exp_start_datetime) for each row that has astrometry_status == -2.

    Returns
    -------
    tuple
        A tuple containing:
        - A SQLAlchemy boolean expression that evaluates to True for rows that should have astrometry monitoring run (i.e., every other row).
        - An integer (0) indicating the new status value for rows that should have astrometry monitoring run.
    """
    indices = [(row.filename, row.reprocess_number) for row in pk_rows]
    selected_pks = []
    for i, (filename, reprocess_number) in enumerate(indices):
        if i % 2 == 0:  # Select every other row (even index)
            selected_pks.append((filename, reprocess_number))

    astrometry_should_run = tuple_(
        L2ScienceMetaTable.filename,
        L2ScienceMetaTable.reprocess_number,
    ).in_(selected_pks)

    return [(astrometry_should_run, 0)]
    
def time_based_astrometry_rule(session, pk_rows):
    """
    Determine which rows should have astrometry monitoring run based on a time-based rule.
    
    Parameters
    ----------
    session : sqlalchemy.orm.Session
        An active SQLAlchemy session used to query the database.
    pk_rows : list of tuples
        A list of tuples containing at least (filename, reprocess_number, exp_start_datetime) for each row that has astrometry_status == -2.

    Returns
    -------
    tuple
        A tuple containing:
        - A SQLAlchemy boolean expression that evaluates to True for rows that should have astrometry monitoring run (i.e., those that are more than 1 hour after the last row that had astrometry monitoring run).
        - An integer (0) indicating the new status value for rows that should have astrometry monitoring run.
    """
    astrometry_time_delta = timedelta(hours=1)
    query_time_delta = timedelta(days=30) # only check the last 30 days of data for astrometry
    last_astrometry_time = session.execute(
        select(L2ScienceMetaTable.exp_start_datetime)
        .where(and_(
            L2ScienceMetaTable.astrometry_status.in_([0,1]),
            L2ScienceMetaTable.exp_start_datetime.is_not(None),
            L2ScienceMetaTable.exp_start_datetime > (datetime.now() - query_time_delta)
        ))
        .order_by(L2ScienceMetaTable.exp_start_datetime.desc())
        .limit(1)
    ).scalar()

    selected_pks = []
    last_time = last_astrometry_time  # may be None
    indices = [(row.filename, row.reprocess_number, row.exp_start_datetime) for row in pk_rows]
    for filename, reprocess_number, exp_start_dt in indices:
        if last_time is None or exp_start_dt > last_time + astrometry_time_delta:
            selected_pks.append((filename, reprocess_number))
            last_time = exp_start_dt

    astrometry_should_run = tuple_(
        L2ScienceMetaTable.filename,
        L2ScienceMetaTable.reprocess_number,
    ).in_(selected_pks)

    return [(astrometry_should_run, 0)]

def generate_message_dict_from_metadata_table(metadata_table_class, monitor_name):
    """
    Generate a message dictionary using the metadata table attributes for the monitor lambda.

    Parameters
    ----------
    metadata_table_class : SQLAlchemy table class
        Like L2ScienceMetaTable
    monitor_name : str
        The name of the monitor associated with this message.

    Returns
    -------
    dict
        A dictionary containing message fields populated from the metadata table
        and monitor information. 

    """
    monitor_dict = {
        MessageKeys.ARCHIVE_BUCKET: metadata_table_class.archive_bucket,
        MessageKeys.ARCHIVE_OBJECT_KEY: metadata_table_class.archive_key,
        MessageKeys.FILE_TYPE: metadata_table_class.file_type,
        MessageKeys.FILENAME: metadata_table_class.filename,
        MessageKeys.FUNCTION_TYPE: FunctionTypes.MONITOR,
        MessageKeys.MONITOR_NAME: monitor_name,
        MessageKeys.REPROCESS_NUMBER: metadata_table_class.reprocess_number,
    }

    return monitor_dict