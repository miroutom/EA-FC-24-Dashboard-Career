from alembic import context

from app import models  # noqa: F401
from app.core import Base, Settings, make_engine

provided = context.config.attributes.get('connection')


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if provided is not None:
    run(provided)
else:
    engine = make_engine(Settings().data_dir)
    with engine.connect() as connection:
        run(connection)
