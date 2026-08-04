import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from rdmt_spire.constants.lambdas import (
    AWS_DBS,
    AWS_PARAMETER_PATH,
    DB_NAME,
    DB_SECRET_NAME,
)
from rdmt_spire.db_tables.base import Base
from rdmt_spire.utilities.aws_utils import fetch_parameters_from_path
from rdmt_spire.utilities.db_utils import get_connection_url, get_engine_from_url

# this is the Alembic Config object, which provides
# access to values within the .ini file in use.
config = context.config
params = fetch_parameters_from_path(AWS_PARAMETER_PATH, expected_parameters=AWS_DBS)
app_logger = config.attributes.get("app_logger")
if app_logger is None:
    app_logger = logging.getLogger("alembic.env")

# Interpret the config file for Python logging.
# This sets up loggers accordingly.
if config.attributes.get("skip_alembic_file_config", False):
    app_logger.info("Skipping fileConfig in alembic env.py; using provided logger configuration.")
elif config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an actual Engine, though the 'url' endpoint
    is still used to configure a URL present in the config file.

    By skipping the creation of an Engine, we don't even need a
    database to be available.
    """
    app_logger.info("Running Alembic migrations in offline mode.")
    url = get_connection_url(db_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME])
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario, we need to create an Engine
    and associate a connection with the context.
    """
    app_logger.info("Running Alembic migrations in online mode.")
    url = get_connection_url(db_name=params[DB_NAME], secret_name=params[DB_SECRET_NAME])
    connectable = get_engine_from_url(url)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()