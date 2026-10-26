import os
import pandas as pd


def extract_data(source: str) -> pd.DataFrame:
    """
    Step 1: EXTRACT
    Reads data from a CSV file into a Pandas DataFrame.
    """
    # 1. Check if source path is specified
    if not source or not str(source).strip():
        raise FileNotFoundError("Pipeline source file path is empty.")

    # 2. Check if file exists on disk
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source file not found at: '{source}'")

    # 3. Check if file format is CSV
    if not source.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")

    # 4. Read CSV into DataFrame
    df = pd.read_csv(source)

    # 5. Check if file is empty
    if df.empty:
        raise ValueError(f"Source file '{source}' is empty (0 records).")

    return df

