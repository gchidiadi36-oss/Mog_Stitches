
import sqlite3

source_path = r"C:\Users\USER\Desktop\Mog_Stitches\mog_stitches.db"
target_path = r"C:\Users\USER\Desktop\Mog_Stitches_GitHub\mog_stitches.db"

source = sqlite3.connect(source_path)
target = sqlite3.connect(target_path)

source.row_factory = sqlite3.Row
target.row_factory = sqlite3.Row

try:
    for table in ("articles", "testimonials"):
        source_rows = source.execute(
            f"SELECT * FROM {table}"
        ).fetchall()

        target_columns = {
            row["name"]
            for row in target.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }

        source_columns = source_rows[0].keys() if source_rows else []

        if not set(source_columns).issubset(target_columns):
            raise RuntimeError(
                f"The {table} table has different columns. "
                "Nothing was committed; check the schema first."
            )

        for row in source_rows:
            existing = target.execute(
                f"SELECT 1 FROM {table} WHERE id = ?",
                (row["id"],)
            ).fetchone()

            if existing:
                continue

            columns = list(row.keys())
            placeholders = ", ".join("?" for _ in columns)
            column_names = ", ".join(columns)

            target.execute(
                f"INSERT INTO {table} ({column_names}) "
                f"VALUES ({placeholders})",
                tuple(row[column] for column in columns)
            )

    target.commit()

    for table in ("articles", "testimonials"):
        count = target.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table}: {count} records")

    print("Content transfer completed.")

except Exception:
    target.rollback()
    raise

finally:
    source.close()
    target.close()
