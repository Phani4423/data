import os
import io
from datetime import datetime

# Third-Party Imports
import requests
import pandas as pd
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.models import UploadedFile
from .abac import validate_permissions
from data.celery import app

API_NINJAS_RANDOM_USER_API_URL = "https://api.api-ninjas.com/v2/randomuser"
API_NINJAS_KEY = "wauPMBxuKFuh+IbSVCcyVg==IFt4kF99StYj9wp8"
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
MYSQL_DB = "new_etl_db"


# Helper Functions
def get_engine():
    url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    return create_engine(url)


# Celery Tasks


@shared_task(bind=True)
def process_upload_task(self, file_bytes, table_name, user_id=None):
    """
    Process uploaded file bytes and save to MySQL table using pandas.
    ABAC enforced.
    """
    import io
    from app.models import User, UploadedFile

    if user_id is None:
        return {"status": "error", "message": "User not provided"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "error", "message": "User not found"}

    if not validate_permissions(user, "upload"):
        return {"status": "error", "message": "Permission denied by ABAC"}

    try:
        # Try reading as CSV, JSON, XML, Excel
        parsers = [
            lambda c: pd.read_csv(io.BytesIO(c)),
            lambda c: pd.read_json(io.BytesIO(c)),
            lambda c: pd.read_xml(io.BytesIO(c)),
            lambda c: pd.read_excel(io.BytesIO(c)),
        ]

        df = None
        last_error = None

        for parser in parsers:
            try:
                df = parser(file_bytes)
                df["uploaded_at"] = datetime.utcnow()
                break
            except Exception as e:
                last_error = e

        if df is None:
            return {
                "status": "error",
                "message": f"Unsupported or unreadable file format. Last error: {last_error}",
            }

        if df.empty:
            return {"status": "error", "message": "File contains no data"}

        engine = get_engine()

        #  1. Store actual data
        df.to_sql(table_name, con=engine, if_exists="append", index=False)

        #  2. UPDATE UploadedFile with row count
        uploaded_file = (
            UploadedFile.objects
            .filter(user_id=user_id, table_name=table_name)
            .order_by("-uploaded_at")
            .first()
        )

        if uploaded_file:
            uploaded_file.rows_added = len(df)
            uploaded_file.save()

        return {
            "status": "success",
            "rows": len(df),
            "table": table_name,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================
# Scenario 2: Real-Time API Ingestion with ABAC
# =========================

# Updated: expects user instance as argument


# Task: Log file upload to MySQL table if user has 'read' permission
from celery import shared_task
from datetime import datetime
from app.models import User


@shared_task(bind=True)
def log_file_upload_task(self, user_id, file_type, file_count, organization):
    """
    Log file upload details to MySQL table.
    This task ALWAYS logs uploads (no ABAC restriction).
    """

    if user_id is None:
        return {"status": "error", "message": "User not provided"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "error", "message": "User not found"}

    try:
        engine = get_engine()

        # ✅ Use transaction (AUTO-COMMIT)
        with engine.begin() as conn:
            insert_sql = (
                "INSERT INTO file_upload_log "
                "(user_name, file_type, file_count, organization, upload_datetime) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
            conn.execute(
                insert_sql,
                (user.username, file_type, file_count, organization, datetime.now()),
            )

        return {
            "status": "success",
            "message": "File upload logged",
            "user": user.username,
            "rows": file_count,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@shared_task(bind=True)
def fetch_random_users_task(self, count, user_id):
    """
    Fetch random users from API and store in MySQL.
    """
    from app.models import User
    import sqlalchemy

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "error", "message": "User not found"}

    if not validate_permissions(user, "upload"):
        return {"status": "error", "message": "Permission denied by ABAC"}

    try:
        headers = {"X-Api-Key": API_NINJAS_KEY}
        response = requests.get(
            API_NINJAS_RANDOM_USER_API_URL,
            headers=headers,
            params={"count": count},
            timeout=10,
        )
        response.raise_for_status()

        users = response.json()

        # ✅ CRITICAL FIX
        if not isinstance(users, list):
            return {"status": "error", "message": "API returned unexpected format"}

        df = pd.DataFrame(users)
        df["fetched_at"] = datetime.utcnow()

        engine = get_engine()
        table_name = "random_users"

        df.to_sql(table_name, con=engine, if_exists="append", index=False)

        return {
            "status": "success",
            "message": f"Random user data successfully stored in table '{table_name}'",
            "table": table_name,
            "rows": len(df),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
