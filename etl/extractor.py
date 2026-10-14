import os
import pandas as pd


def extract_data(source: str) -> pd.DataFrame:
    """
    Simple CSV Extractor:
    Checks if the source file exists and reads it into a Pandas DataFrame.
    """
    if not source or not str(source).strip():
        raise FileNotFoundError("Pipeline source file path is empty or not configured.")

    if not os.path.exists(source):
        raise FileNotFoundError(f"Source file not found at: '{source}'")

    if not source.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported.")

    df = pd.read_csv(source)

    if df.empty:
        raise ValueError(f"Source file '{source}' is empty (0 records).")

    return df
