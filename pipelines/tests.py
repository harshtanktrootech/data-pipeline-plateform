import pytest
from django.db.utils import IntegrityError
from pipelines.models import Pipeline


# Concept 1: Using Fixtures from conftest.py in Model Tests

def test_pipeline_create(sample_pipeline, admin_user):
    """
    Test using fixtures from conftest.py.
    Notice:
      - We didn't import sample_pipeline or admin_user!
      - Pytest automatically injected them.
    """
    assert sample_pipeline.name == "Sales Analytics Pipeline"
    assert sample_pipeline.status == "active"
    assert sample_pipeline.created_by == admin_user
    assert str(sample_pipeline) == "Sales Analytics Pipeline"
    assert sample_pipeline.table_name == "sales_analytics_pipeline_data"



# Concept 2: @pytest.mark.django_db (Granting Database Access)

@pytest.mark.django_db
def test_custom_table_name(admin_user):
    """
    Test that if a custom table_name is explicitly provided,
    Pipeline.save() preserves it instead of auto-generating one.
    """
    custom_pipeline = Pipeline.objects.create(
        name="Inventory Pipeline",
        table_name="custom_inventory_tbl",
        created_by=admin_user,
    )
    assert custom_pipeline.table_name == "custom_inventory_tbl"



# Concept 3: Database Constraints with pytest.raises

@pytest.mark.django_db
def test_duplicate_name_error(admin_user):
    """
    Pipeline.name has unique=True.
    Test that creating two pipelines with identical names raises IntegrityError.
    """
    Pipeline.objects.create(name="HR Payroll", created_by=admin_user)

    with pytest.raises(IntegrityError):
        Pipeline.objects.create(name="HR Payroll", created_by=admin_user)



# Concept 4: Combining @pytest.mark.parametrize + @pytest.mark.django_db

@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw_name, expected_table_name",
    [
        ("Customer Data 2026", "customer_data_2026_data"),
        ("Healthcare & Medical Records!", "healthcare_medical_records_data"),
        ("  Leading and Trailing Spaces  ", "leading_and_trailing_spaces_data"),
        ("crm_leads_v2", "crm_leads_v2_data"),
    ],
)
def test_auto_table_name(admin_user, raw_name, expected_table_name):
    """
    Parametrized test to verify table_name generation logic
    across various pipeline names.
    """
    pipeline = Pipeline.objects.create(name=raw_name, created_by=admin_user)
    assert pipeline.table_name == expected_table_name
