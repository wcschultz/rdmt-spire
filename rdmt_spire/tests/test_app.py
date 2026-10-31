import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

#import pytest
# from rdmt_spire.app import handler
# from rdmt_spire.constants.codes import StatusCodes
from ..app import handler
from ..constants.codes import StatusCodes
from ..constants.lambdas import FunctionTypes, MessageKeys

#TODO: add mock s3 handler / mock SQS message

class LambdaContextMock():
    # Simulates the lambda function context that is needed to get the account ID
    def __init__(self, function_name='test-function'):
        self.invoked_function_arn = f"arn:aws:lambda:us-east-1:123456789012:function:{function_name}"

def test_lambda_app():
    """
    Testing lambda handler
    """
    context = LambdaContextMock()
    base_message = {
        'archiveBucket':        'test_bucket',
        'archiveObjectKey':     'somefile.txt',
        'checksum':             'test checksum (hex)', #32 char MD5 hex
        'reprocessingState':    'none', # 'none', 'reprocessed', or 'data_release'
        'reprocessingId':       'for_testing', #string set by HLPP operators
        'externalSource':       '', 
        'filename':             'somefile.txt',
        'fileType':             'science_wfi_level_2', 
        'fileSubType':          'image', # optional and still unclear what this will actually be in ops
        'fileSize':             '100000000', # in bytes 
        'fileCreationTimestamp':'2023-10-05T14:48:00.000Z', # in UTC
        'program_category':     'CCS',
        'program_subcategory':  'HLWA',
    }

    event={'Records':[{'body': json.dumps({'Message': json.dumps(base_message)})}]}
    response=handler(event,context) 
    assert response['statusCode'] == StatusCodes.FAILURE # This is a failure because we have not implemented AWS mocking yet
    assert 'error_message' in response['body'][0]

    base_message['function_type'] = 'monitor'
    base_message['monitor_name'] = 'noise_1f'
    
    no_monitor_message = {**base_message, 'monitor_name': 'non_existing_monitor'}
    event={'Records':[{'body': json.dumps(no_monitor_message)}]}
    response=handler(event,context)

    no_file_message = {**base_message, 'archiveObjectKey':''}
    event={'Records':[{'body': json.dumps(no_file_message)}]}
    response=handler(event,context)

    report_event = {'function_type':'report'}
    response=handler(report_event,context)
    assert response['statusCode'] == StatusCodes.FAILURE
    assert 'error_message' in response['body'][0]

    meta_event = {'function_type':'meta_check'}
    with patch('rdmt_spire.lambdas.metadata_check.fetch_parameters_from_path', return_value={}):
        response=handler(meta_event,context)
    assert response['statusCode'] == StatusCodes.FAILURE # TODO: Currently generates a database connection error. Need to mock the database to fix.
    assert 'error_message' in response['body'][0]


@pytest.mark.parametrize('string_bodies', [True, False])
def test_handler_ingest_batch_decodes_messages_and_timestamps(string_bodies):
    messages = [{'filename': 'first.fits'}, {'filename': 'second.fits'}]
    records = []
    for index, message in enumerate(messages):
        body = {'Message': json.dumps(message)}
        records.append({
            'body': json.dumps(body) if string_bodies else body,
            'attributes': {'SentTimestamp': str(1000 + index * 500)},
        })
    expected = {'statusCode': StatusCodes.SUCCESS, 'body': []}
    with patch('rdmt_spire.app.ingest_batch', return_value=expected) as ingest:
        assert handler({'Records': records}, LambdaContextMock()) == expected
    ingest.assert_called_once_with(
        messages,
        [datetime.fromtimestamp(1, timezone.utc), datetime.fromtimestamp(1.5, timezone.utc)],
        '123456789012',
    )


@pytest.mark.parametrize('mixed', [True, False])
def test_handler_rejects_batched_monitor_messages(mixed):
    monitor = {MessageKeys.FUNCTION_TYPE: FunctionTypes.MONITOR}
    bodies = [{'Message': json.dumps({'filename': 'first.fits'})} if mixed else monitor, monitor]
    event = {'Records': [{'body': json.dumps(body)} for body in bodies]}
    with patch('rdmt_spire.app.ingest_batch') as ingest:
        response = handler(event, LambdaContextMock())
    assert response['statusCode'] == StatusCodes.BAD_LAMBDA_BATCH_SIZE
    ingest.assert_not_called()
