import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from django.db import connection
from pipelines.models import Pipeline
from etl.runner import run_pipeline

user, _ = User.objects.get_or_create(username="admin")

# 1. Test Customers Pipeline
p1, _ = Pipeline.objects.get_or_create(
    name="Customers Pipeline",
    defaults={
        "source": "data/customers.csv",
        "table_name": "customers_data",
        "created_by": user,
    }
)
print("=== Running Customers Pipeline ===")
res1 = run_pipeline(p1)
print("Result:", res1)

# 2. Test Cricketers Pipeline
p2, _ = Pipeline.objects.get_or_create(
    name="Cricketers Pipeline",
    defaults={
        "source": "data/cricketers.csv",
        "table_name": "cricketers_data",
        "created_by": user,
    }
)
print("\n=== Running Cricketers Pipeline ===")
res2 = run_pipeline(p2)
print("Result:", res2)

# 3. Test Sales Pipeline
p3, _ = Pipeline.objects.get_or_create(
    name="Sales Pipeline",
    defaults={
        "source": "data/sales.csv",
        "table_name": "sales_data",
        "created_by": user,
    }
)
print("\n=== Running Sales Pipeline ===")
res3 = run_pipeline(p3)
print("Result:", res3)


# 4. Test employees Pipeline
p4, _ = Pipeline.objects.get_or_create(
    name="Employees Pipeline",
    defaults={
        "source": "data/employees.csv",
        "table_name": "employees_data",
        "created_by": user,
    }
)
print("\n=== Running Employees Pipeline ===")
res4 = run_pipeline(p4)
print("Result:", res4)



# 5. Test students Pipeline
p5, _ = Pipeline.objects.get_or_create(
    name="Students Pipeline",
    defaults={
        "source": "data/students.csv",
        "table_name": "students_data",
        "created_by": user,
    }
)
print("\n=== Running Students Pipeline ===")
res5 = run_pipeline(p5)
print("Result:", res5)


# 5. Verify tables and rows created in Database
# print("\n=== Database Verification ===")
# with connection.cursor() as cursor:
#     for tbl in ["customers_data", "cricketers_data", "sales_data"]:
#         cursor.execute(f'SELECT count(*) FROM "{tbl}";')
#         count = cursor.fetchone()[0]
#         print(f"Table '{tbl}' total rows in DB: {count}")
