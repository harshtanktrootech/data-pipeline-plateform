# Data Pipeline Platform

A self-service ETL (Extract, Transform, Load) platform built with Django, Celery, and PostgreSQL. It allows users to define data pipelines from CSV datasets, run them manually or on automated cron schedules, and monitor execution metrics with a complete audit trail.

---

## 🚀 High-Level Architecture & Flow

```
   [ CSV Files (data/) ]
             │
             ▼
   [ Pipeline Configuration ]  ── (User / Admin via Web UI or REST API)
             │
             ├──► Manual Run ──────┐
             │                     ▼
             └──► Scheduled Run ─► [ Celery Beat & Worker ]
                                   │
                                   ▼
                           [ ETL Engine ]
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
                 Extract       Transform       Load
               (Read CSV)     (Clean Data)   (Insert into PostgreSQL)
                                   │
                                   ▼
                       [ Monitoring & Auditing ]
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
            Pipeline Executions              Audit Logs
            (Status & Row counts)       (User activity & errors)
```

---

## 📁 Project Structure

| Folder / Module | Responsibility |
| :--- | :--- |
| **`pipelines/`** | Manages pipeline definitions, dataset source mappings, and cron schedule settings. |
| **`etl/`** | The core data engine: `extractor.py` (reads CSV), `transformer.py` (cleans data), `loader.py` (writes to DB), and `runner.py` (coordinates all steps). |
| **`executions/`** | Stores execution history (`PipelineExecution`), row counts, errors, and Celery background tasks (`tasks.py`). |
| **`audit/`** | Records user activity and execution outcomes (`AuditLog`) for compliance and debugging. |
| **`accounts/`** | Handles authentication, login/registration, and Role-Based Access Control (Admin, Operator, Viewer). |
| **`dashboard/`** | Aggregates summary statistics (success/failed ratios, avg run duration, active pipelines). |
| **`data/`** | Directory storing raw CSV dataset files used as pipeline sources. |
| **`config/`** | Django project configuration (`settings.py`, `urls.py`, `celery.py`). |

---

## 🔄 How a Pipeline Executes (Step-by-Step)

1. **Trigger**: A run is triggered manually (via Web UI / API) or automatically by **Celery Beat** on a cron schedule.
2. **Extract**: `etl/extractor.py` verifies the CSV file in `data/` and loads it into a Pandas DataFrame.
3. **Transform**: `etl/transformer.py` normalizes column names into `snake_case`, drops blank rows, and cleans null/empty values.
4. **Load**: `etl/loader.py` dynamically creates the destination table in PostgreSQL (if it doesn't already exist) and inserts cleaned records using parameterized SQL.
5. **Log & Audit**:
   - `executions/models.py` creates a `PipelineExecution` record tracking rows extracted, added, and failed.
   - `audit/services.py` writes an `AuditLog` entry documenting the user, action, and any row-level error details.

---

## 👥 User Roles & Permissions (RBAC)

* **Admin**: Full access (manage users, create/edit/delete/run all pipelines, view all audit logs).
* **Operator**: Can create and execute pipelines, and manage pipelines they own.
* **Viewer**: Read-only access to view pipelines, dashboards, and execution history.

---

## 🛠️ Quickstart (Running Locally)

### 1. Prerequisites
* Python 3.12+
* PostgreSQL (running on port `5432`)
* Redis (running on port `6379`)

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Database Migration
```bash
python manage.py migrate
```

### 4. Start the Application

Open separate terminals to run each service:

* **Django Web Server**:
  ```bash
  python manage.py runserver
  ```
  Access the web interface at `http://127.0.0.1:8000/`.

* **Celery Worker** (Processes background execution tasks):
  ```bash
  celery -A config worker -l info
  ```

* **Celery Beat** (Dispatches scheduled cron jobs):
  ```bash
  celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  ```

