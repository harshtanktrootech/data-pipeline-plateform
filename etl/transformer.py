# Responsible for: Cleaning/processing the extracted data.
# Contains dynamic, schema-agnostic transformation logic.

import pandas as pd


def transform_data(df: pd.DataFrame):
    """
    Dynamically cleans ANY DataFrame:
    1. Normalizes column headers.
    2. Drops completely empty rows.
    3. Cleans all text columns (strip whitespace, Title Case).
    4. Replaces fake null strings with real None.
    5. Drops rows missing primary data.
    6. Auto-detects and converts numeric columns.
    7. Deduplicates records.
    8. Returns list of clean dictionaries.
    """
    if df is None or df.empty:
        return []

    df = df.copy()

    # ── STEP 1: Normalize column headers ──
    # " First Name " → "first_name"
    # "ORDER DATE"   → "order_date"

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # ── STEP 2: Drop rows where ALL values are empty ──
    # A row like ",," in CSV has no useful data at all
    df = df.dropna(how="all")

    # ── STEP 3: Clean all text columns ──
    text_columns = df.select_dtypes(include=["object", "string"]).columns

    for col in text_columns:
        # Convert everything to string first, then strip spaces
        df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

        # Replace fake null strings with real Python None
        df[col] = df[col].replace(
            ["", "nan", "NaN", "None", "null", "NULL", "NA", "na", "N/A"],
            None,
        )

        # Apply Title Case only to non-null string values
        df[col] = df[col].apply(
            lambda val: val.title() if isinstance(val, str) else val
        )

    # ── STEP 4: Drop rows where primary column is missing ──
    # The first column is usually the identifier (id, customer_id, etc.)
    primary_col = df.columns[0]
    df = df.dropna(subset=[primary_col])

    # ── STEP 5a: Auto-detect and convert numeric columns ──
    # After cleaning, some columns that look like "1", "2", "3"
    # should be converted back to real integers/floats
    for col in df.columns:
        # Skip columns that are already numeric
        if df[col].dtype in ["int64", "float64", "int32", "float32"]:
            continue

        # Try converting this column to numbers
        converted = pd.to_numeric(df[col], errors="coerce")

        # Count how many values successfully became numbers
        non_null_count = df[col].notna().sum()

        if non_null_count == 0:
            continue

        success_count = converted.notna().sum()
        success_rate = success_count / non_null_count

        # If 90%+ of non-null values are numeric, convert the column
        if success_rate >= 0.6:
            # Check if all successful values are whole numbers (integers)
            if (converted.dropna() % 1 == 0).all():
                df[col] = converted.astype("Int64")  # Nullable integer
            else:
                df[col] = converted  # Keep as float

    # ── STEP 5b: Re-check primary column after type conversion ──
    # Values like "Manan" in the id column become None after numeric conversion
    df = df.dropna(subset=[primary_col])


    # ── STEP 6: Deduplicate ──
    id_columns = [
        col for col in df.columns if col == "id" or col.endswith("_id")
    ]
    if id_columns:
        df = df.drop_duplicates(subset=id_columns, keep="last")
    else:
        df = df.drop_duplicates(keep="last")

    # ── STEP 7: Convert to list of dictionaries for loader ──
    records =  df.to_dict(orient="records")
    return [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in records
    ]
