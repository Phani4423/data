from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response

from .serializers import FileUploadSerializer, CarFetchSerializer

import pandas as pd
import io
from datetime import datetime
import requests
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError


# MySQL connection (change if your credentials are different)
DB_URL = "mysql+pymysql://root:root@localhost:3306/etl_db"
engine = create_engine(DB_URL, echo=False, future=True)


#   EXTRACT (from FILE)
def load_file_to_dataframe(django_file):
    """
    Extract step (FILE SOURCE)

    Try reading the uploaded file as CSV, JSON, XML, Excel (in that order).
    Returns: (df, detected_type)
    Raises: ValueError if none work.
    """
    content = django_file.read()  # bytes

    parsers = [
        ("csv",   lambda c: pd.read_csv(io.BytesIO(c))),
        ("json",  lambda c: pd.read_json(io.BytesIO(c))),
        ("xml",   lambda c: pd.read_xml(io.BytesIO(c))),
        ("excel", lambda c: pd.read_excel(io.BytesIO(c))),
    ]

    last_error = None
    for fmt, parser in parsers:
        try:
            df = parser(content)

            #  small TRANSFORM step: add uploaded_at metadata
            df["uploaded_at"] = datetime.utcnow()
            return df, fmt
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"Unsupported or unreadable file format. Last error: {last_error}")


#   LOAD (common for all)
def save_dataframe_to_mysql(df: pd.DataFrame, table_name: str = "car_data"):
    """
    Load step (common)

    Save DataFrame to MySQL in tabular form.
    - Creates table if it doesn't exist.
    - Appends rows if it does.
    """
    if df.empty:
        raise ValueError("File contains no data")

    df.to_sql(table_name, engine, if_exists="append", index=False)



#   EXTRACT (from EXTERNAL CARS API)


API_KEY = "wauPMBxuKFuh+IbSVCcyVg==IFt4kF99StYj9wp8"
BASE_URL = "https://api.api-ninjas.com/v1/cars"


def extract_car_data(make: str, model: str):
    """
    Extract step (API SOURCE)

    Calls external API and fetches car data based on make+model.
    """
    url = f"{BASE_URL}?make={make}&model={model}"
    headers = {"X-Api-Key": API_KEY}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise ValueError(f"API Error: {response.text}")

    data = response.json()

    if not data:
        raise ValueError("No data returned from API")

    return data


#   TRANSFORM (API data)
def transform_car_data(raw_data):
    """
    Transform step (API SOURCE)

    Convert JSON list into a DataFrame and add metadata.
    """
    df = pd.DataFrame(raw_data)

    # Add ETL metadata
    df["fetched_at"] = datetime.utcnow()

    return df


#   VIEW 1: FILE → ETL → MySQL (OLD CODE)
class FileUploadAPIView(generics.GenericAPIView):
    """
    POST /upload/

    Form-data:
      - table_name (optional): MySQL table (default: uploaded_data)
      - file (required): CSV / JSON / XML / Excel file

    Behaviour:
      - Extracts: reads file and detects type
      - Transforms: adds 'uploaded_at'
      - Loads: saves into MySQL in tabular format
      - Returns JSON with info + preview of data
    """

    serializer_class = FileUploadSerializer
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        #  Validate request (file + optional table_name)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        django_file = serializer.validated_data["file"]
        table_name = serializer.validated_data.get("table_name") or "uploaded_data"

        try:
            # 1️ EXTRACT + small TRANSFORM (from file)
            df, detected_type = load_file_to_dataframe(django_file)

            # 2️ LOAD into MySQL
            save_dataframe_to_mysql(df, table_name)

            preview_df = df.head(5)
            preview = {
                "columns": list(preview_df.columns),
                "rows": preview_df.to_dict(orient="records"),
            }

            from django.http import JsonResponse

            return JsonResponse(
                {
                    "message": "File uploaded and stored in MySQL successfully",
                    "source": "file",
                    "detected_type": detected_type,
                    "table_name": table_name,
                    "rows_inserted": len(df),
                    "preview": preview,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except SQLAlchemyError as db_err:
            return Response(
                {"error": f"MySQL Error: {str(db_err)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class FetchCarDataAPIView(generics.GenericAPIView):
    """
    POST /fetch-cars/

    JSON Body:
    {
        "make": "Audi",
        "model": "A4",
    }

    Behaviour:
      - Extract: calls external cars API using API key
      - Transform: JSON → DataFrame + add 'fetched_at'
      - Load: save into MySQL
      - Returns JSON with info + preview of data
    """

    serializer_class = CarFetchSerializer
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        # ✅ Validate input (make, model)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        make = serializer.validated_data["make"]
        model = serializer.validated_data["model"]

        try:
            # 1️⃣ EXTRACT (from external API)
            raw_data = extract_car_data(make, model)

            # 2️⃣ TRANSFORM (JSON → DataFrame)
            df = transform_car_data(raw_data)

            # 3️⃣ LOAD into MySQL
            save_dataframe_to_mysql(df)

            preview_df = df.head(5)

            return Response(
                {
                    "message": "Car data fetched from external API and stored in MySQL successfully",
                    "source": "external_api",
                    "api_make": make,
                    "api_model": model,
                    "rows_inserted": len(df),
                    "preview": preview_df.to_dict(orient="records"),
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except SQLAlchemyError as db_err:
            return Response(
                {"error": f"MySQL Error: {str(db_err)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
