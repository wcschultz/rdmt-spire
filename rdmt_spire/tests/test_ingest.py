from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from ..constants.codes import StatusCodes
from ..constants.dmd import FileTypes
from ..constants.lambdas import (
    L2_SCIENCE_EXPOSURE_CONFIG,
    MessageKeys,
)
from ..lambdas.ingest import create_table_class_from_message, ingest_batch


def test_create_table_class_from_message_uses_exposure_status_config():
    message = {
        MessageKeys.FILE_TYPE: FileTypes.L2_SCIENCE,
        MessageKeys.EXPOSURE_TYPE: None,
        MessageKeys.FILENAME: "test.fits",
        MessageKeys.ARCHIVE_BUCKET: "test-bucket",
        MessageKeys.ARCHIVE_OBJECT_KEY: "test.fits",
        MessageKeys.FILE_CREATION_TIMESTAMP: "2026-01-02T03:04:05.000Z",
    }
    observation_info = {
        "program_num": 1,
        "execution_num": 2,
        "pass_num": 3,
        "segment_num": 4,
        "obs_num": 5,
        "visit_num": 6,
        "exposure_num": 7,
        "visit_id": "visit-id",
        "detector": "detector",
        "optical_element": "filter",
    }

    with patch(
        "rdmt_spire.lambdas.ingest.get_info_from_filename",
        return_value=observation_info,
    ):
        for exposure_type, config in L2_SCIENCE_EXPOSURE_CONFIG.items():
            message[MessageKeys.EXPOSURE_TYPE] = exposure_type
            meta_table = create_table_class_from_message(message)

            assert meta_table.exposure_type == config["exposure_type"]
            for status_column, status_value in config["status_values"].items():
                assert getattr(meta_table, status_column) == int(status_value)


def test_ingest_batch_runs_single_ingestion_for_every_message():
    messages = [{'filename': 'first.fits'}, {'filename': 'second.fits'}]
    timestamps = [datetime(2026, 1, day, tzinfo=timezone.utc) for day in (1, 2)]
    responses = [
        {'statusCode': StatusCodes.SUCCESS, 'body': [{'error_message': name}]}
        for name in ('first', 'second')
    ]
    with patch('rdmt_spire.lambdas.ingest.ingest_single', side_effect=responses) as ingest:
        response = ingest_batch(messages, timestamps, '123456789012')
    assert response == {'statusCode': StatusCodes.SUCCESS,
                        'body': [{'error_message': 'first'}, {'error_message': 'second'}]}
    assert ingest.call_count == 2
    for index, invocation in enumerate(ingest.call_args_list):
        assert invocation.args == (messages[index], timestamps[index], '123456789012')


@pytest.mark.parametrize('failure', [
    {'statusCode': StatusCodes.REPROCESS_NUM_DETERMINATION_FAIL,
     'body': [{'error_message': 'invalid reprocessing state'}]},
    {'statusCode': StatusCodes.METADATA_TABLE_CREATION_FAIL,
     'body': [{'error_message': 'unsupported file type'}]},
    {'statusCode': StatusCodes.SQS_SEND_FAIL,
     'body': [{'error_message': 'queue failure'}]},
    ValueError('invalid message'),
])
def test_ingest_batch_continues_after_failure(failure):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    success = {'statusCode': StatusCodes.SUCCESS, 'body': [{'error_message': 'ingested'}]}
    with patch('rdmt_spire.lambdas.ingest.ingest_single', side_effect=[failure, success]) as ingest:
        response = ingest_batch([{}, {}], [timestamp, timestamp], '123456789012')
    assert ingest.call_count == 2
    assert response['statusCode'] == (StatusCodes.FAILURE if isinstance(failure, Exception)
                                    else failure['statusCode'])
    assert len(response['body']) == 2
    assert response['body'][1] == success['body'][0]


def test_ingest_batch_preserves_first_failure_status():
    responses = [
        {'statusCode': StatusCodes.SQS_SEND_FAIL, 'body': [{'error_message': 'first failure'}]},
        {'statusCode': StatusCodes.REPROCESS_NUM_DETERMINATION_FAIL,
         'body': [{'error_message': 'second failure'}]},
    ]
    with patch('rdmt_spire.lambdas.ingest.ingest_single', side_effect=responses):
        response = ingest_batch([{}, {}], [None, None], '123456789012')
    assert response['statusCode'] == StatusCodes.SQS_SEND_FAIL
    assert response['body'] == responses[0]['body'] + responses[1]['body']


def test_ingest_batch_rejects_mismatched_timestamps_before_ingesting():
    with patch('rdmt_spire.lambdas.ingest.ingest_single') as ingest:
        with pytest.raises(ValueError, match='corresponding notification datetime'):
            ingest_batch([{}], [], '123456789012')
    ingest.assert_not_called()


def test_ingest_batch_empty():
    with patch('rdmt_spire.lambdas.ingest.ingest_single') as ingest:
        assert ingest_batch([], [], '123456789012') == {'statusCode': StatusCodes.SUCCESS, 'body': []}
    ingest.assert_not_called()