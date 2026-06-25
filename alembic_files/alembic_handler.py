import json
import logging
import os
import shutil
from pathlib import Path

import boto3

from rdmt_spire.constants.codes import StatusCodes
from rdmt_spire.constants.lambdas import (
    ALEMBIC_VERSIONS_BUCKET,
    AWS_DBS,
    AWS_PARAMETER_PATH,
    AWS_S3_BUCKETS,
)
from rdmt_spire.utilities.aws_utils import (
    fetch_parameters_from_path,
    remove_from_s3,
    write_to_s3,
)
from rdmt_spire.utilities.db_utils import (
    download_migration_scripts_from_s3,
    run_alembic_downgrade,
    run_alembic_upgrade,
)

logger = logging.getLogger()
for old_handler in logger.handlers:
    logger.removeHandler(old_handler)

new_handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)-7.7s [%(name)s] %(message)s')
new_handler.setFormatter(formatter)
logger.addHandler(new_handler)
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

def handler(event, context):
    """Lambda function handler run to update the Spire database in AWS."""
    params = fetch_parameters_from_path(AWS_PARAMETER_PATH, expected_parameters=AWS_DBS + AWS_S3_BUCKETS)
    alembic_file_local_path = Path('/tmp/alembic_files')

    change_type = event.get("change_type")
    allow_update = event.get("allow_update")
    revision_str = event.get("revision_str")
    manual_revision = event.get('manual_revision')

    if manual_revision:
        logger.info('manual_revision = True thus saving revision file, but manual upgrade using revision string will be needed.')
        allow_update = False
    else:
         manual_revision = False # handle case where manual_revision is not specified (default of .get() is None)

    if allow_update:
        logger.info("allow_update = True thus any changes will be pushed to the database.")
    elif allow_update is None:
        logger.warning("allow_update not set by input message. Using default (False).")
        allow_update = False
    else:
        logger.info("allow_update = False thus no changes will be executed.")

    # Download version files and prep the alembic directory for changes
    try:
        logger.info(f"Downloading version files from: {params[ALEMBIC_VERSIONS_BUCKET]} to {alembic_file_local_path}")
        download_migration_scripts_from_s3(params[ALEMBIC_VERSIONS_BUCKET], alembic_file_local_path, s3_client=s3_client)
        logger.info("Download complete.")

        env_path = "/var/task/alembic_files/env.py"
        mako_path = "/var/task/alembic_files/script.py.mako" 

        logger.info(f'Copying required alembic files to {alembic_file_local_path}')
        shutil.copy(env_path, alembic_file_local_path)
        shutil.copy(mako_path, alembic_file_local_path)
        logger.info('Copy complete.')
    except Exception as e:
        logger.error(f"{e.__class__.__name__}: {str(e)}")
        return {
            'statusCode': StatusCodes.ALEMBIC_FAILED_VERSIONS_DOWNLOAD,
            'body': json.dumps({
                'message': f'Could not access/download the alembic version files from s3 bucket({params[ALEMBIC_VERSIONS_BUCKET]}).',
                'error': f"{e.__class__.__name__}: {str(e)}"
            })
        }

    # if attempting to push the database history forward
    if change_type == "upgrade":
        try:
            logger.info('Starting alembic checking/upgrade process.')
            db_update_bool, revision_path = run_alembic_upgrade('alembic.ini', str(alembic_file_local_path), revision_str, allow_update=allow_update, save_revision=manual_revision)
            logger.info('alembic executions complete.')
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {str(e)}")
            return {
                'statusCode': StatusCodes.ALEMBIC_UPDATE_FAILURE,
                'body': json.dumps({
                    'message': 'Could not upgrade the database tables successfully.',
                    'error': f"{e.__class__.__name__}: {str(e)}"
                })
            }

        if db_update_bool and (revision_path is not None) and (allow_update or manual_revision):
            # TODO: add an try-except here to re-downgrade and remove upgrade if writing the version file fails
            rev_object_name = os.path.basename(revision_path)
            write_to_s3(revision_path, params[ALEMBIC_VERSIONS_BUCKET], rev_object_name, s3_client=s3_client)

        # prepare an exit message
        if db_update_bool and allow_update:
            exit_message = 'Successfully updated the database tables using alembic.'
        elif db_update_bool and manual_revision:
            exit_message = 'Successfully configured database update using alembic, revision saved as manual_revision = True, not upgraded as allow_upgrade = False.'
        elif db_update_bool:
            exit_message = 'Successfully configured database update using alembic but not upgraded as allow_upgrade = False.'
        else:
            exit_message = 'Database does not need updates.'

    # if attempting to revert to a previous database change
    elif change_type == "downgrade":
        try:
            logger.info('Starting alembic downgrade process.')
            versions_to_delete = run_alembic_downgrade('alembic.ini', str(alembic_file_local_path), revision_str, allow_update=allow_update)
            logger.info('alembic executions complete.')
        except Exception as e:
            logger.error(f"{e.__class__.__name__}: {str(e)}")
            return {
                'statusCode': StatusCodes.ALEMBIC_UPDATE_FAILURE,
                'body': json.dumps({
                    'message': 'Could not upgrade the database tables successfully.',
                    'error': f"{e.__class__.__name__}: {str(e)}"
                })
            }
        
        if versions_to_delete and allow_update:
            # TODO: think about this implementation more
            for revision in versions_to_delete:
                rev_object_name = f"{os.path.basename(revision.path)}"
                remove_from_s3(params[ALEMBIC_VERSIONS_BUCKET], rev_object_name, s3_client=s3_client)

        # prepare an exit message
        if versions_to_delete and allow_update:
            exit_message = 'Successfully updated the database tables using alembic.'
        elif versions_to_delete:
            exit_message = 'Successfully configured database update using alembic but not upgraded as allow_upgrade = False.'
        else:
            exit_message = 'Database not updated.'

    logger.info(f'alembic_handler finished: {exit_message}')
    return {
        'statusCode': StatusCodes.SUCCESS,
        'body': json.dumps({
            'message': exit_message,
        })
    }