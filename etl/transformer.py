import pandas as pd

def transform_data(df):
    """
    Standard ETL Data Cleaning:
    1. Standardizes headers to clean snake_case.
    2. Drops fully empty rows.
    3. Strips whitespace and normalizes empty/null values to None.
    4. Removes duplicate records.
    5. Returns cleaned list of dictionaries.
    """
    if df is None or df.empty:
        raise ValueError("Data Validation Error: Input dataset is empty.")

    df = df.copy()

    # 1. Standardize column names: lowercase, strip, spaces to underscores
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    # 2. Drop completely empty rows
    df = df.dropna(how="all")

    # 3. Strip whitespace from string columns and convert missing strings to None
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace(["", "nan", "NaN", "None", "null", "NULL", "NA", "N/A"], None)

    # 4. Remove duplicate rows
    df = df.drop_duplicates()

    # 5. Validation check: Ensure valid rows remain
    if df.empty:
        raise ValueError("Data Validation Error: 0 valid records remained after cleaning.")

    # 6. Convert to list of dicts, ensuring pandas NaN is Python None for SQL
    records = df.to_dict(orient="records")
    return [
        {col: (None if pd.isna(val) else val) for col, val in row.items()}
        for row in records
    ]
