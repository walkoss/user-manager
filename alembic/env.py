import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from user_manager.models import DeclarativeBase


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.

config = context.config
config.set_main_option("sqlalchemy.url", os.environ["DB_URI"])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = DeclarativeBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=target_metadata.schema,
            include_schemas=True,
            include_object=lambda o, n, t, *_: t != "table"
            or o.schema == target_metadata.schema,
        )

        with context.begin_transaction():
            connection.execute(f"CREATE SCHEMA IF NOT EXISTS {target_metadata.schema};")
            """
            By default search_path is setted to "$user",public 
            that why alembic can't create foreign keys correctly
            """
            context.execute("SET search_path TO public")
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
