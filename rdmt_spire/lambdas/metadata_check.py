import json
import logging

import boto3
from sqlalchemy import case, inspect as sa_inspect, or_, select, update
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
    # Generate three dictionaries to keep track of: the SQL statements to run,
    # their corresponding result rows, and the destination SQS URLs.
    sql_statements = {}
    sql_results = {}
    sqs_urls = {}

    params = fetch_parameters_from_path(AWS_PARAMETER_PATH, expected_parameters=AWS_MONITOR_QUEUES + AWS_DBS)

    # Determine which query(s) to run based on the requested check type.
    # Currently, only 'astrometry' is supported.
    if message_dict[MessageKeys.METADATA_CHECK_TYPE] == 'astrometry':
        # Query: select rows with astrometry_status == 0 (i.e., need monitoring).
        sql_statements['astrometry'] = select(L2ScienceMetaTable).where(L2ScienceMetaTable.astrometry_status == 0)
        # Resolve the SQS queue URL for astrometry monitoring for the given account.
        sqs_urls['astrometry'] = get_sqs_url(
                params[ASTROMETRY_MONITOR_QUEUE], 
                account_id=aws_account_id
            )
    elif message_dict[MessageKeys.METADATA_CHECK_TYPE] == 'clean_statuses':
        # Query: update any rows with any _status == 0 to -1 (i.e., reset them to not run).
        # Derive _status columns directly from the ORM mapper so this stays in sync
        # with the table definition without manual updates.
        status_cols = [
            getattr(L2ScienceMetaTable, attr.key)
            for attr in sa_inspect(L2ScienceMetaTable).column_attrs
            if attr.key.endswith('_status')
        ]
        stmt = (
            update(L2ScienceMetaTable)
            .where(or_(*[col == 0 for col in status_cols]))
            .values({col.key: case((col == 0, -1), else_=col) for col in status_cols})
            .execution_options(synchronize_session=False)
        )
        with Session(connect_to_db(database_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME])) as session:
            session.execute(stmt)
            session.commit()
    else:
        # Unsupported check type: log and return an informative response.
        error_message = f'metadata_check_function is not yet implemented for {MessageKeys.METADATA_CHECK_TYPE} = {message_dict[MessageKeys.METADATA_CHECK_TYPE]}.'
        logger.error(error_message)
        return {'statusCode': StatusCodes.NOT_YET_IMPLEMENTED,
                'body': [{'error_message':error_message}]}

    logger.info(f'Running metadata check for {MessageKeys.METADATA_CHECK_TYPE} = {message_dict[MessageKeys.METADATA_CHECK_TYPE]}.')
    # Run the query(s) to identify files that need monitors and bundle them together
    logger.info('connecting to the db')
    sql_engine = connect_to_db(database_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME])

    logger.info(f"Querying the metadata table for the following keys: {', '.join(sql_statements.keys())}")
    with Session(sql_engine) as session:
        for key, stmnt in sql_statements.items():
            # Execute the query and materialize all matching rows for this key.
            result_rows = session.scalars(stmnt).all()
            sql_results[key] = result_rows
            logger.info(f'Found {len(result_rows)} rows that match {key} criteria.')

    # Send the correct messages to the correct queues
    logger.info('Sending messages...')
    sqs = boto3.client("sqs", region_name='us-east-1')
    
    for key, row_list in sql_results.items():
        for row in row_list:
            monitor_dict = generate_message_dict_from_metadata_table(row, key)
            try:
                # Send the message to the queue associated with this key.
                response = sqs.send_message(
                    QueueUrl=sqs_urls[key],
                    MessageBody=json.dumps(monitor_dict)
                )
                logger.info(f'Message sent for {key}. Response: {response}')
            except Exception as e:
                logger.error(f"Failed in sending message: {e}")
                # TODO: how do we want to handle this error correctly?
                raise e

    logger.info('Successfully sent all messages. Metadata check complete,')

    return {'statusCode': StatusCodes.SUCCESS,
                'body': [{'message':'metadata_check_function ran successfully.'}]} 

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