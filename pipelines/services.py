from pipelines.models import Pipeline


def validate_pipeline_can_run(pipeline):

    if pipeline.status != "active":
        raise ValueError("Inactive pipeline cannot be executed.")

    return True