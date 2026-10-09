import pandas as pd


def transform_data(df: pd.DataFrame):
    """
    Dynamically cleans ANY DataFrame:
    1. Normalizes column headers.
    2. Drops completely empty rows.
    3. Cleans all text columns (strip whitespace, Title Case for text, lowercase for emails).
    4. Replaces fake null strings with real None.
    5. Drops rows missing primary data.
    6. Auto-detects and converts numeric columns.
    7. Deduplicates records.
    8. Returns list of clean dictionaries.
    """
    if df is None or df.empty:
        return []

    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    df = df.dropna(how="all")

    text_columns = df.select_dtypes(include=["object", "string"]).columns

    for col in text_columns:
        df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        df[col] = df[col].replace(
            ["", "nan", "NaN", "None", "null", "NULL", "NA", "na", "N/A"],
            None,
        )

        # Lowercase email addresses, Title Case for regular text, preserve None
        df[col] = df[col].apply(
            lambda val: val.lower() if isinstance(val, str) and "@" in val
            else (val.title() if isinstance(val, str) else val)
        )

    primary_col = df.columns[0]
    df = df.dropna(subset=[primary_col])

    for col in df.columns:
        if df[col].dtype in ["int64", "float64", "int32", "float32"]:
            continue

        converted = pd.to_numeric(df[col], errors="coerce")
        non_null_count = df[col].notna().sum()

        if non_null_count == 0:
            continue

        success_count = converted.notna().sum()
        success_rate = success_count / non_null_count

        if success_rate >= 0.6:           
            if (converted.dropna() % 1 == 0).all():
                df[col] = converted.astype("Int64")  # Nullable integer
            else:
                df[col] = converted  # Keep as float

    df = df.dropna(subset=[primary_col])

    id_columns = [
        col for col in df.columns if col == "id" or col.endswith("_id")
    ]
    if id_columns:
        df = df.drop_duplicates(subset=id_columns, keep="last")
    else:
        df = df.drop_duplicates(keep="last")
        
    records = df.to_dict(orient="records")
    return [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in records
    ]

