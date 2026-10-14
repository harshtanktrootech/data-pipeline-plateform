import re
from django.db import connection, transaction


def clean_name(name: str) -> str:
    """Sanitizes names into safe SQL identifiers."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(name).strip().lower())
    return f"col_{clean}" if clean and clean[0].isdigit() else clean or "col"


def get_column_type(values: list) -> str:
    """Infers SQL type from sample Python values."""
    sample = next((v for v in values if v is not None), None)
    if isinstance(sample, bool):
        return "BOOLEAN"
    if isinstance(sample, int):
        return "BIGINT"
    if isinstance(sample, float):
        return "DOUBLE PRECISION"
    return "TEXT"


def load_data(cleaned_data: list, table_name: str) -> int:
    """
    Creates the PostgreSQL table if it doesn't exist and bulk-inserts records.
    """
    if not cleaned_data or not table_name:
        return 0

    table = clean_name(table_name)
    columns = list(cleaned_data[0].keys())
    clean_cols = [clean_name(c) for c in columns]

    with connection.cursor() as cursor:
        # 1. Create table if not exists
        col_defs = [
            f'"{col}" {get_column_type([row.get(orig) for row in cleaned_data])}'
            for orig, col in zip(columns, clean_cols)
        ]
        cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)});')

        # 2. Bulk insert records inside an atomic transaction
        cols_str = ", ".join([f'"{c}"' for c in clean_cols])
        placeholders = ", ".join(["%s"] * len(clean_cols))
        rows = [[row.get(c) for c in columns] for row in cleaned_data]

        with transaction.atomic():
            cursor.executemany(f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders});', rows)

    return len(cleaned_data)
