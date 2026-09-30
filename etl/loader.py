import re
from django.db import connection, transaction


def sanitize_identifier(name: str) -> str:
    """
    Sanitizes table and column names to ensure safe SQL identifiers.
    Replaces spaces and special characters with underscores.
    """
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(name).strip().lower())
    if clean and clean[0].isdigit():
        clean = f"col_{clean}"
    return clean or "column"


def infer_sql_type(values, db_vendor="postgresql") -> str:
    """
    Infers the appropriate SQL column type from sample Python values.
    """
    sample_val = next((v for v in values if v is not None), None)

    if sample_val is None:
        return "TEXT"
    if isinstance(sample_val, bool):
        return "BOOLEAN"
    if isinstance(sample_val, int):
        return "BIGINT"
    if isinstance(sample_val, float):
        return "DOUBLE PRECISION" if "postgres" in db_vendor else "REAL"
    return "TEXT"


def load_data(cleaned_data: list, table_name: str) -> int:
    """
    Dynamically creates the database table (if it doesn't exist)
    and loads the cleaned records into it.
    """
    if not cleaned_data or not table_name:
        return 0

    table = sanitize_identifier(table_name)
    columns = list(cleaned_data[0].keys())
    clean_cols = [sanitize_identifier(col) for col in columns]

    with connection.cursor() as cursor:
        db_vendor = connection.vendor

        # 1. Build dynamic column definitions
        col_definitions = []
        for col, clean_col in zip(columns, clean_cols):
            col_values = [row.get(col) for row in cleaned_data]
            sql_type = infer_sql_type(col_values, db_vendor)
            col_definitions.append(f'"{clean_col}" {sql_type}')

        cols_sql = ", ".join(col_definitions)

        # 2. Dynamically CREATE TABLE IF NOT EXISTS
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({cols_sql});'
        cursor.execute(create_table_sql)

        # 3. Bulk INSERT data inside a transaction
        quoted_cols = ", ".join([f'"{c}"' for c in clean_cols])
        placeholders = ", ".join(["%s"] * len(clean_cols))
        insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders});'

        rows_to_insert = [
            [row.get(col) for col in columns]
            for row in cleaned_data
        ]

        with transaction.atomic():
            cursor.executemany(insert_sql, rows_to_insert)

    return len(cleaned_data)
