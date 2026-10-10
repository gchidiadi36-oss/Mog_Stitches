
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "mog_stitches.db")


class HybridRow(dict):
    """Allow row access by column name or numeric index."""

    def __getitem__(self, key):
        if isinstance(key, int):
            key = list(self.keys())[key]
        return super().__getitem__(key)


def hybrid_row_factory(cursor):
    if cursor.description is None:
        return None

    columns = [column.name for column in cursor.description]

    def make_row(row):
        return HybridRow(zip(columns, row))

    return make_row

class PostgresConnection:
    """Compatibility layer for existing SQLite-style SQL queries."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        sql = sql.replace("?", "%s")
        return self.connection.execute(sql, parameters)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __getattr__(self, name):
        return getattr(self.connection, name)


def get_db():
    if DATABASE_URL:
        import psycopg

        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]

        connection = psycopg.connect(
            url,
            row_factory=hybrid_row_factory
        )
        return PostgresConnection(connection)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    conn = get_db()
    is_postgres = bool(DATABASE_URL)

    try:
        if is_postgres:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS gallery (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    category TEXT NOT NULL DEFAULT 'Other',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                ALTER TABLE gallery
                ADD COLUMN IF NOT EXISTS category
                TEXT NOT NULL DEFAULT 'Other'
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    featured_image TEXT,
                    published INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS testimonials (
                    id SERIAL PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    review TEXT NOT NULL,
                    rating INTEGER NOT NULL DEFAULT 5,
                    approved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS gallery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    category TEXT NOT NULL DEFAULT 'Other',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            columns = [
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(gallery)"
                ).fetchall()
            ]

            if "category" not in columns:
                conn.execute("""
                    ALTER TABLE gallery
                    ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'
                """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    featured_image TEXT,
                    published INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS testimonials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    review TEXT NOT NULL,
                    rating INTEGER NOT NULL DEFAULT 5,
                    approved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()

    finally:
        conn.close()
