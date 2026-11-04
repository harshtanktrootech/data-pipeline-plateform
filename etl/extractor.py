import csv
import os
import pandas as pd


def extract_data(source: str):
    """
    Step 1: EXTRACT
    Reads CSV into a DataFrame and captures any malformed rows with line numbers.
    """
    if not source or not os.path.exists(source) or not source.lower().endswith(".csv"):
        raise FileNotFoundError(f"Valid CSV file not found at: '{source}'")

    valid_rows = []
    failed_rows = []
    indices = []

    with open(source, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        headers = [h.strip() for h in next(reader, [])]
        expected_cols = len(headers)

        if not headers:
            raise ValueError(f"Source file '{source}' is empty.")

        for line_num, row in enumerate(reader, start=2):
            if not row or not any(row):  # Skip blank lines
                continue

            cleaned_values = [v.strip() for v in row]
            row_dict = dict(zip(headers, cleaned_values))

            if len(row) != expected_cols:
                failed_rows.append({
                    "row_number": line_num,
                    "data": row_dict,
                    "error": f"Expected {expected_cols} columns, found {len(row)}",
                })
            else:
                valid_rows.append(row_dict)
                indices.append(line_num)

    if not valid_rows and not failed_rows:
        raise ValueError(f"Source file '{source}' has no data rows.")

    if valid_rows:
        df = pd.DataFrame(valid_rows, index=indices)
    else:
        df = pd.DataFrame(columns=headers)

    return df, failed_rows
