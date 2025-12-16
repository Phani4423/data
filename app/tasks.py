
import os
from datetime import datetime

# Third-Party Imports
import requests
import pandas as pd
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from .abac import abac_check
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
def process_upload_task(self, file_bytes, table_name, user_role="data_engineer"):
    """
    Process uploaded file bytes and save to MySQL table using pandas. ABAC enforced.
    """
    import io
    resource_attrs = {
        "resource_type": "file",
        "file_format": table_name.split('.')[-1] if '.' in table_name else "unknown",
        "sensitivity": "low"
    }
    if not abac_check(user_role, "ingest", resource_attrs):
        return {"status": "error", "message": "Permission denied by ABAC"}
    try:
        # Try reading as CSV, JSON, XML, Excel (in that order)
        parsers = [
            ("csv",   lambda c: pd.read_csv(io.BytesIO(c))),
            ("json",  lambda c: pd.read_json(io.BytesIO(c))),
            ("xml",   lambda c: pd.read_xml(io.BytesIO(c))),
            ("excel", lambda c: pd.read_excel(io.BytesIO(c))),
        ]
        last_error = None
        for fmt, parser in parsers:
            try:
                df = parser(file_bytes)
                df["uploaded_at"] = datetime.utcnow()
                break
            except Exception as e:
                last_error = e
                df = None
        if df is None:
            return {"status": "error", "message": f"Unsupported or unreadable file format. Last error: {last_error}"}
        if df.empty:
            return {"status": "error", "message": "File contains no data"}
        engine = get_engine()
        df.to_sql(table_name, con=engine, if_exists="append", index=False)
        return {"status": "success", "rows": len(df), "table": table_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}






# =========================
# Scenario 2: Real-Time API Ingestion with ABAC
# =========================
@shared_task(bind=True)
def fetch_random_users_task(self, count=5, user_role="data_engineer"):
   
    # --- ABAC Check ---
    resource_attrs = {
        "resource_type": "api",
        "source": "external_app",
        "sensitivity": "high"
    }
    if not abac_check(user_role, "ingest", resource_attrs):
        return {"status": "error", "message": "Permission denied by ABAC"}

    try:
        # --- Fetch API Data ---
        headers = {"X-Api-Key": API_NINJAS_KEY}
        users = []
        batch_size = 30  # API limit per request
        remaining = count
        while remaining > 0:
            req_count = min(batch_size, remaining)
            params = {"count": req_count}
            response = requests.get(API_NINJAS_RANDOM_USER_API_URL, headers=headers, params=params)
            response.raise_for_status()
            batch_users = response.json()
            if isinstance(batch_users, list):
                users.extend(batch_users)
            else:
                users.append(batch_users)
            remaining -= req_count

        # --- Store in DB with dynamic schema update ---
        engine = get_engine()
        import pandas as pd
        import datetime
        import sqlalchemy
        df = pd.DataFrame(users)
        df["fetched_at"] = datetime.datetime.utcnow()

        table_name = "random_users"
        insp = sqlalchemy.inspect(engine)
        # If table does not exist, create it with all columns from df
        if not insp.has_table(table_name):
            df.head(0).to_sql(table_name, con=engine, if_exists="replace", index=False)
        else:
            # Add missing columns
            existing_cols = set([col['name'] for col in insp.get_columns(table_name)])
            with engine.connect() as conn:
                for col in df.columns:
                    if col not in existing_cols:
                        alter_sql = f'ALTER TABLE {table_name} ADD COLUMN `{col}` TEXT'
                        try:
                            conn.execute(sqlalchemy.text(alter_sql))
                        except Exception as e:
                            pass
        # Re-inspect columns after adding
        insp = sqlalchemy.inspect(engine)
        final_cols = set([col['name'] for col in insp.get_columns(table_name)])
        # Only keep columns that exist in the table
        df = df[[col for col in df.columns if col in final_cols]]
        df.to_sql(table_name, con=engine, if_exists="append", index=False)

        return {
            "status": "success",
            "message": f"Random user data successfully stored in table '{table_name}'",
            "table": table_name,
            "rows": len(df)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}




