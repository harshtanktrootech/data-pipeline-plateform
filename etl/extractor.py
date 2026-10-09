import os
import requests
import pandas as pd


def extract_data(source, source_type=None):
    if not source or not str(source).strip():
        raise FileNotFoundError("Pipeline source file path is empty or not configured.")

    # 1. Check if source is a URL
    if source.startswith(("http://", "https://")):
        response = requests.get(source)
        response.raise_for_status()

        data = response.json()

        return pd.DataFrame(data)

    # 2. Check if local file exists
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source file not found at: '{source}'")

    # 2. If source_type is not provided, get it from file extension
    if source_type is None:

        _, extension = os.path.splitext(source)

        source_type = extension.lower().replace(".", "")

    # 3. Read file based on format
    if source_type == "csv":

        return pd.read_csv(source)

    elif source_type == "json":

        return pd.read_json(source)

    elif source_type in ["xlsx", "xls"]:

        return pd.read_excel(source)

    else:

        raise ValueError(
            f"Unsupported format: {source_type}"
        )