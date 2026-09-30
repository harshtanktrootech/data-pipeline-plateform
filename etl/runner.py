import time
from etl.extractor import extract_data
from etl.transformer import transform_data
from etl.loader import load_data
from pipelines.models import Pipeline

def run_pipeline(pipeline: Pipeline, source_type=None, max_retries=3):
    attempt = 0
    start_time = time.time()

    while attempt < max_retries:
        attempt += 1

        try:
            # 1. Extract
            raw_data = extract_data(pipeline.source, source_type)

            # 2. Transform
            clean_data = transform_data(raw_data)
             
            # 3. Load dynamically into pipeline table
            records_loaded = load_data(clean_data, table_name=pipeline.table_name)

            duration = round(time.time() - start_time, 4)
            return {
                "status": "SUCCESS",
                "records_extracted": raw_data.shape[0],
                "records_processed": len(clean_data),
                "records_loaded": records_loaded,
                "duration_seconds": duration,
                "attempts": attempt,
                "error": None,
            }

        except Exception as e:
            if attempt >= max_retries:
                duration = round(time.time() - start_time, 4)
                return {
                    "status": "FAILED",
                    "records_extracted": 0,
                    "records_processed": 0,
                    "records_loaded": 0,
                    "duration_seconds": duration,
                    "attempts": attempt,
                    "error": str(e),
                }
            time.sleep(0.5)
