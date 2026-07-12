import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """Return the request-local SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):
    """Close the request-local connection, if one was opened."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """Create missing tables and insert any missing stable seed rows."""
    db = get_db()

    with current_app.open_resource("schema.sql") as schema_file:
        db.executescript(schema_file.read().decode("utf-8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database schema and seed the catalog."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
