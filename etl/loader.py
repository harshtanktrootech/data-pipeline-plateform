import re
from django.db import connection, transaction


def clean_identifier(name: str) -> str:
    """
    Cleans a table or column name into a safe SQL identifier:
    Converts to lowercase, replaces special characters with underscores.
    Example: 'Students Data' -> 'students_data'
    """
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(name).strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "data_table"


def load_data(records: list, table_name: str) -> dict:
    """
    Step 3: LOAD
    Loads cleaned records into a PostgreSQL database table:
    1. Creates the table if it doesn't exist (using TEXT columns for compatibility).
    2. Inserts records row-by-row with parameterized SQL.
    3. Tracks added records and any failed rows.
    """
    result = {
        "records_added": 0,
        "records_failed": 0,
        "success_rows": [],
        "failed_rows": [],
    }

    if not records or not table_name:
        return result

    # Normalize records into (row_number, row_dict) pairs
    row_items = []
    for idx, item in enumerate(records):
        if isinstance(item, dict) and "data" in item:
            row_items.append((item.get("row_number", idx + 2), item["data"]))
        elif isinstance(item, dict):
            row_items.append((idx + 2, item))

    if not row_items:
        return result

    safe_table = clean_identifier(table_name)
    columns = list(row_items[0][1].keys())
    safe_columns = [clean_identifier(c) for c in columns]

    with connection.cursor() as cursor:
        # 1. Create table if it does not exist
        column_defs = [f'"{col}" TEXT' for col in safe_columns]
        create_sql = f'CREATE TABLE IF NOT EXISTS "{safe_table}" ({", ".join(column_defs)});'
        cursor.execute(create_sql)

        # 2. Prepare parameterized INSERT SQL
        cols_sql = ", ".join([f'"{col}"' for col in safe_columns])
        placeholders = ", ".join(["%s"] * len(safe_columns))
        insert_sql = f'INSERT INTO "{safe_table}" ({cols_sql}) VALUES ({placeholders});'

        # 3. Insert each row into the database
        for line_num, row_data in row_items:
            try:
                values = [row_data.get(c) for c in columns]
                with transaction.atomic():
                    cursor.execute(insert_sql, values)

                result["records_added"] += 1
                result["success_rows"].append({
                    "row_number": line_num,
                    "data": row_data,
                    "action": "added",
                })
            except Exception as err:
                error_msg = str(err).split("\n")[0].strip()
                result["failed_rows"].append({
                    "row_number": line_num,
                    "data": row_data,
                    "error": error_msg,
                })

    result["records_failed"] = len(result["failed_rows"])
    return result

