
import os
import sqlite3
import psycopg
from psycopg.rows import dict_row

source_db = r"C:\Users\USER\Desktop\Mog_Stitches\mog_stitches.db"
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is not set in this Command Prompt.")

if not os.path.exists(source_db):
    raise FileNotFoundError(f"Source database not found: {source_db}")

src = sqlite3.connect(source_db)
src.row_factory = sqlite3.Row

tables = ["admins", "gallery", "articles", "testimonials"]

try:
    with psycopg.connect(database_url, row_factory=dict_row) as dst:
        with dst.cursor() as cur:
            for table in tables:
                rows = src.execute(f"SELECT * FROM {table}").fetchall()
                print(f"{table}: found {len(rows)} source records")

                for row in rows:
                    data = dict(row)
                    columns = list(data.keys())

                    if table == "admins":
                        cur.execute(
                            """
                            INSERT INTO admins (id, username, password)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (username) DO NOTHING
                            """,
                            (data["id"], data["username"], data["password"])
                        )
                        continue

                    placeholders = ", ".join(["%s"] * len(columns))
                    column_names = ", ".join(columns)

                    if table == "gallery":
                        conflict = "ON CONFLICT (id) DO NOTHING"
                    elif table == "articles":
                        conflict = "ON CONFLICT (id) DO NOTHING"
                    else:
                        conflict = "ON CONFLICT (id) DO NOTHING"

                    cur.execute(
                        f"INSERT INTO {table} ({column_names}) "
                        f"VALUES ({placeholders}) {conflict}",
                        tuple(data[column] for column in columns)
                    )

                print(f"{table}: import processed")

            # Keep future generated IDs above the imported IDs.
            for table in tables:
                cur.execute(
                    """
                    SELECT setval(
                        pg_get_serial_sequence(%s, 'id'),
                        GREATEST(COALESCE((SELECT MAX(id) FROM
                        """ + table + """), 1), 1),
                        EXISTS (SELECT 1 FROM """ + table + """)
                    )
                    """,
                    (table,)
                )

    print("Migration completed successfully.")

finally:
    src.close()
