import json
from unittest.mock import patch

#import pytest
# from rdmt_spire.app import handler
# from rdmt_spire.constants.codes import StatusCodes
from ..app import handler
from ..constants.codes import StatusCodes

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
