import pandas as pd


def clean_column_name(col_name: str) -> str:
    """
    Cleans a column name:
    Converts to lowercase, replaces spaces and dashes with underscores,
    and removes special characters.
    Example: ' Customer Name # ' -> 'customer_name'
    """
    clean = str(col_name).strip().lower()
    clean = clean.replace(" ", "_").replace("-", "_")
    clean = "".join(c for c in clean if c.isalnum() or c == "_")
    return clean or "column"


def transform_data(df: pd.DataFrame):
    """
    Step 2: TRANSFORM
    Cleans the raw DataFrame:
    1. Standardizes column names to lowercase snake_case.
    2. Drops completely empty rows.
    3. Strips whitespace from text values and converts null markers to None.
    4. Separates valid records and failed rows.
    """
    if df is None or df.empty:
        raise ValueError("Data Validation Error: Input dataset is empty.")

    df = df.copy()

    # 1. Clean column headers
    df.columns = [clean_column_name(col) for col in df.columns]

    # 2. Drop completely empty rows
    df = df.dropna(how="all")

    valid_records = []
    failed_rows = []

    # 3. Process each row
    for idx, row in df.iterrows():
        line_num = idx + 2  # Row number in original CSV (1-indexed + header)

        cleaned_row = {}
        is_row_empty = True

        for col, val in row.items():
            if pd.isna(val) or val is None:
                cleaned_row[col] = None
            else:
                str_val = str(val).strip()
                if str_val.lower() in ["", "nan", "none", "null", "n/a"]:
                    cleaned_row[col] = None
                else:
                    cleaned_row[col] = str_val
                    is_row_empty = False

        # Skip rows that are completely blank
        if is_row_empty:
            continue

        valid_records.append({
            "row_number": line_num,
            "data": cleaned_row,
        })

    return valid_records, failed_rows

