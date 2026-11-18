import pytest
import pandas as pd
from etl.transformer import clean_column_name, transform_data


# Concept 1: @pytest.mark.parametrize (Testing multiple inputs cleanly)
@pytest.mark.parametrize(
    "raw_input, expected_output",
    [
        (" Customer Name ", "customer_name"),      
        ("Order-ID", "order_id"),                   
        ("Total Amount ($)", "total_amount_"),      
        ("FIRST_NAME", "first_name"),               
        ("###", "column"),                          
        ("", "column"),                             
    ],
)
def test_clean_column_name(raw_input, expected_output):
    """
    Test clean_column_name with multiple edge cases.
    Pytest will run this function 6 times, once for each pair above!
    """
    assert clean_column_name(raw_input) == expected_output



# Concept 2: with pytest.raises (Testing that exceptions are raised)
def test_transform_data_none_raises_error():
    """
    Verify that passing None as the dataframe raises a ValueError.
    """
    with pytest.raises(ValueError) as exc_info:
        transform_data(None)

    # Check that the error message is what we expect
    assert "Input dataset is None" in str(exc_info.value)



# Concept 3: Standard assertions & testing data structures
def test_transform_data_empty_dataframe():
    """
    Verify that an empty DataFrame returns empty lists for both records and errors.
    """
    df = pd.DataFrame()
    valid_records, failed_rows = transform_data(df)

    assert valid_records == []
    assert failed_rows == []


def test_transform_data_cleans_values_and_handles_nulls():
    """
    Test that transform_data:
      1. Cleans column headers (e.g., ' Full Name ' -> 'full_name')
      2. Strips whitespace from values ('  John Doe  ' -> 'John Doe')
      3. Converts null markers ('N/A', 'null', 'nan') to None
    """
    raw_data = {
        " Full Name ": ["  Alice Smith  ", "Bob Jones", "   ", "Harsh   TANK"],
        "Age": ["25", "N/A", "null", "  23"],
        "City": ["New York", None, "   ", None],  # Contains Python None to test missing values
    }
    df = pd.DataFrame(raw_data)

    valid_records, failed_rows = transform_data(df)

    # 4 rows were input, 1 was completely empty, so 3 valid records remain!
    assert len(valid_records) == 3
    assert failed_rows == []

    # Verify cleaned data for all valid rows at once
    actual_rows = [record["data"] for record in valid_records]
    assert actual_rows == [
        {"full_name": "Alice Smith", "age": "25", "city": "New York"},
        {"full_name": "Bob Jones", "age": None, "city": None},
        {"full_name": "Harsh   TANK", "age": "23", "city": None},
    ]
