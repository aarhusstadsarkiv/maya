"""
Module for managing and applying database schema migrations using SQLite.

This module defines a `Migration` class that handles the execution and tracking of SQL-based migrations
on an SQLite database. It ensures that each migration is applied only once by maintaining a `migrations`
table within the database. The module performs the following key functions:

- Initializes the SQLite connection and checks for the existence of the migrations tracking table.
- Applies SQL migrations provided as a dictionary of migration keys and SQL strings.
- Tracks applied migrations to avoid re-execution.
- Commits each migration to the database and logs the process.
- Provides a method to close the database connection.

Typical usage:

    migrations = {
        "001_create_users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
        "002_add_email_to_users": "ALTER TABLE users ADD COLUMN email TEXT;"
    }

    migrator = Migration("example.db", migrations)
    migrator.run_migrations()
    migrator.close()
"""

import sqlite3
import logging

log = logging.getLogger(__name__)


MIGRATION_TABLE_SQL = """
CREATE TABLE migrations (
    id INTEGER PRIMARY KEY,
    migration_key TEXT NOT NULL,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
) STRICT;
"""


class Migration:
    def __init__(self, db_path, migrations):
        self.migrations = migrations
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_migrations_table_if_not_exists()

    def _check_migrations_table_exists(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations';")
        result = self.cursor.fetchone()
        return result is not None

    def _create_migrations_table_if_not_exists(self):
        if not self._check_migrations_table_exists():
            self.cursor.execute(MIGRATION_TABLE_SQL)
            self.conn.commit()
            log.info("Migrations table created.")
        else:
            log.info("Migrations table already exists.")

    def _has_migration_been_applied(self, migration_key):
        self.cursor.execute("SELECT 1 FROM migrations WHERE migration_key = ?", (migration_key,))
        return self.cursor.fetchone() is not None

    def _apply_migration(self, migration_key, sql):

        # Get all statements from the sql string
        sql_statements = sql.split(";")

        if not self._has_migration_been_applied(migration_key):
            for statement in sql_statements:
                self.cursor.execute(statement)
                self.conn.commit()

            log.info(f"SQL for {migration_key} executed")
            self.cursor.execute("INSERT INTO migrations (migration_key) VALUES (?)", (migration_key,))
            self.conn.commit()
            log.info(f"Migration {migration_key} recorded")

    def run_migrations(self):
        for migration_key, sql in self.migrations.items():
            self._apply_migration(migration_key, sql)

    def close(self):
        self.conn.close()
