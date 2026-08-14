import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .constants.codes import StatusCodes
from .constants.lambdas import FunctionTypes, MessageKeys
from .lambdas.ingest import ingest_batch, ingest_single
from .lambdas.metadata_check import metadata_check_function
from .lambdas.monitor import monitor_function
from .lambdas.report import report_function

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event: Dict, context: Dict) -> Dict[str, int| List[Dict[Any, Any]]]:
    """Main runner function that is executed within each Lambda function on AWS.

    Parameters
    ----------
    event : Dict
        The notification/event that triggered the Lambda function to execute.
        For this tool, it will be from EventBridge or an SQS queue we are developing.
    context : Dict
        Contains information about the execution including things like the lambda function's name,
        version, invoking function's ARN, invoking account id, etc.

    Returns
    -------
    A JSON dictionary containing a status code and some body information depending on what is needed.
    """
    try:
        aws_account_id = context.invoked_function_arn.split(":")[4]
        if 'Records' in event:
            # batch_size must be 1 for most execution options
            if len(event['Records']) == 1:
                body = event['Records'][0]['body']
                if isinstance(body, str):
                    body = json.loads(body)

                # the SQS from DMD will not have "function_type" in it
                if MessageKeys.FUNCTION_TYPE not in body.keys():
                    message_dict = json.loads(body['Message'])
                    unix_timestamp = float(event['Records'][0]['attributes']['SentTimestamp'])/1000.0
                    notification_datetime = datetime.fromtimestamp(unix_timestamp, timezone.utc)
                    return ingest_single(message_dict, notification_datetime, aws_account_id)
                elif body[MessageKeys.FUNCTION_TYPE] == FunctionTypes.MONITOR:
                    return monitor_function(body)
                elif body[MessageKeys.FUNCTION_TYPE] == FunctionTypes.METADATA_CHECK:
                    return metadata_check_function(body, aws_account_id)
                elif body[MessageKeys.FUNCTION_TYPE] == FunctionTypes.REPORT_GEN:
                    report_type = body.get(MessageKeys.REPORT_TYPE)
                    return report_function(report_type)

            else:
                function_type_checks = [MessageKeys.FUNCTION_TYPE in json.loads(rec['body']['Message']).keys() for rec in event['Records']]

                # if no function_type is specified, the 'ingest_function' should be used
                if sum(function_type_checks) == 0:
                    message_dicts = [json.loads(rec['body']['Message']) for rec in event['Records']]
                    notification_datetimes = [float(rec['attributes']['SentTimestamp'])/1000.0 for rec in event['Records']]
                    return ingest_batch(message_dicts, notification_datetimes)
                else:
                    return {'statusCode': StatusCodes.BAD_LAMBDA_BATCH_SIZE,
                    'body': [{'error_message':'A lambda function not running ingest_function received more than 1 request.'}]}

        else:
            return {'statusCode': StatusCodes.BAD_EVENT_FORMAT,
                    'body': [{'error_message':'Incorrect event format provided to app.py'}]}
    except Exception as e:
        logger.error(f"Failed somewhere in app.py with error: {e}", exc_info=True)
        return {
            'statusCode': StatusCodes.FAILURE,
            'body': [{'error_message':f"{e}"}],
        }
