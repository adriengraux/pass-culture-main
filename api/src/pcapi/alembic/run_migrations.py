from alembic import context
from sqlalchemy import create_engine

from pcapi import settings
from pcapi.alembic import migration_types
from pcapi.models import db


target_metadata = db.metadata


def include_object(object, name, type_, reflected, compare_to) -> bool:  # pylint: disable=redefined-builtin
    # Don't generate DROP tables with autogenerate
    # https://alembic.sqlalchemy.org/en/latest/cookbook.html#don-t-generate-any-drop-table-directives-with-autogenerate
    if type_ == "table" and reflected and compare_to is None:
        return False
    if name in ("transaction", "activity"):
        return False
    return True


def render_item(type_, obj, autogen_context):
    if type_ == "type" and isinstance(obj, migration_types.MagicEnum):
        autogen_context.imports.add(f"import {obj.enum_class.__module__}")
        autogen_context.imports.add("from pcapi.alembic import migration_types")
        return "types.%r" % obj
    return False


def run_migrations() -> None:
    db_options = []
    if settings.DB_MIGRATION_LOCK_TIMEOUT:
        db_options.append("-c lock_timeout=%i" % settings.DB_MIGRATION_LOCK_TIMEOUT)
    if settings.DB_MIGRATION_STATEMENT_TIMEOUT:
        db_options.append("-c statement_timeout=%i" % settings.DB_MIGRATION_STATEMENT_TIMEOUT)

    connectable = create_engine(settings.DATABASE_URL, connect_args={"options": " ".join(db_options)})

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=True,
            transaction_per_migration=True,
            compare_server_default=True,
            user_module_prefix="migration_types.",
        )
        with context.begin_transaction():
            context.run_migrations()
