from rest_framework.permissions import IsAuthenticated

# Utility to get allowed features for a role
def get_allowed_features(user_role):
    features = []
    # File features
    if abac_check(user_role, 'ingest', {'resource_type': 'file'}):
        features.append('File Ingest')
    if abac_check(user_role, 'transform', {'resource_type': 'file'}):
        features.append('File Transform')
    if abac_check(user_role, 'load', {'resource_type': 'file'}):
        features.append('File Load')
    if abac_check(user_role, 'read', {'resource_type': 'file'}):
        features.append('File Read')
    # API features
    if abac_check(user_role, 'ingest', {'resource_type': 'api'}):
        features.append('API Ingest')
    if abac_check(user_role, 'validate', {'resource_type': 'api'}):
        features.append('API Validate')
    return features

# /me/ endpoint
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.views import APIView

class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Get current user info and allowed features.")
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        features = get_allowed_features(role)
        return Response({
            'username': user.username,
            'role': role,
            'features': features
        })
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
# ABAC import
from .abac import abac_check
from .serializers_auth import RegisterSerializer, LoginSerializer
# ========== User Registration =============

from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "username": user.username, "role": user.role})
        return Response(serializer.errors, status=400)

# ========== User Login =============
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(username=serializer.validated_data["username"], password=serializer.validated_data["password"])
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"token": token.key, "username": user.username, "role": user.role})
            return Response({"error": "Invalid credentials"}, status=400)
        return Response(serializer.errors, status=400)
from celery.result import AsyncResult
from rest_framework.views import APIView


from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response

from .serializers import FileUploadSerializer, RandomUserFetchSerializer

import pandas as pd
import io
from datetime import datetime
import requests
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

class TaskStatusAPIView(APIView):
    def get(self, request, task_id):
        from data.celery import app  # Import your Celery app
        result = AsyncResult(task_id, app=app)
        response = {
            "task_id": task_id,
            "status": result.status,
        }
        if result.status == "SUCCESS":
            try:
                response["result"] = result.get(timeout=1)
            except Exception as e:
                response["result"] = str(e)
        else:
            response["result"] = None
        return Response(response)
# MySQL connection (change if your credentials are different)
DB_URL = "mysql+pymysql://root:root@localhost:3306/new_etl_db"
engine = create_engine(DB_URL, echo=False, future=True)


#   EXTRACT (from FILE)
def load_file_to_dataframe(django_file):
    
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

    if df.empty:
        raise ValueError("File contains no data")

    df.to_sql(table_name, engine, if_exists="append", index=False)



#   VIEW 1: FILE → ETL → MySQL (OLD CODE)
class FileUploadAPIView(generics.GenericAPIView):
    """
    POST /upload/

    Form-data:
      - table_name (optional): MySQL table (default: uploaded_data)
      - file (required): CSV / JSON / XML / Excel file

    Behaviour:
      - This endpoint now enqueues a background Celery task to process the file.
      - Returns a `task_id` which can be used to inspect results with a Celery result backend.
    """

    serializer_class = FileUploadSerializer
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        # ABAC: Only allow if user has permission to ingest file
        user = request.user
        user_role = getattr(user, 'role', None)
        if not abac_check(user_role, 'ingest', {"resource_type": "file"}):
            return Response({"error": "Access denied by ABAC policy."}, status=status.HTTP_403_FORBIDDEN)

        #  Validate request (file + optional table_name)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        django_file = serializer.validated_data["file"]
        table_name = serializer.validated_data.get("table_name") or "uploaded_data"

        try:
            # read bytes and enqueue a Celery task
            file_bytes = django_file.read()
            from app.tasks import process_upload_task

            task = process_upload_task.delay(file_bytes, table_name)
            return Response({"message": "Task queued", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class FetchRandomUsersAPIView(generics.GenericAPIView):
   

    serializer_class = RandomUserFetchSerializer
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        # ABAC: Only allow if user has permission to ingest API
        user = request.user
        user_role = getattr(user, 'role', None)
        if not abac_check(user_role, 'ingest', {"resource_type": "api"}):
            return Response({"error": "Access denied by ABAC policy."}, status=status.HTTP_403_FORBIDDEN)

        #  Validate input (count is optional)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        count = serializer.validated_data.get("count", 2)

        try:
            from app.tasks import fetch_random_users_task

            task = fetch_random_users_task.delay(count)
            return Response({"message": "Task queued", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
