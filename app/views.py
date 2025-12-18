from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import generics, status
from .models import UploadedFile


# List all uploaded files for users with read permission
class UploadedFileListAPIView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    from .serializers import UploadedFileSerializer

    serializer_class = UploadedFileSerializer

    def get_queryset(self):
        user = self.request.user
        from .abac import validate_permissions

        if not validate_permissions(user, "read"):
            return UploadedFile.objects.none()

        # Filter files by user's organizations if user has organizations
        queryset = UploadedFile.objects.all()
        if user.organizations.exists():
            queryset = queryset.filter(
                user__organizations__in=user.organizations.all()
            ).distinct()

        return queryset

    def get(self, request, *args, **kwargs):
        user = request.user
        from .abac import validate_permissions

        if not validate_permissions(user, "read"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = self.get_queryset()
        files = queryset.values(
            "id",
            "filename",
            "uploaded_at",
            "table_name",
            "rows_added",
            "user__username",
            "user__organizations__name",
        )
        return Response(list(files))


from rest_framework.permissions import IsAuthenticated


# Utility to get allowed features for a role
def get_allowed_features(user):
    features = []
    if validate_permissions(user, "upload"):
        features.append("upload_file")
        features.append("fetch_random_users")
    if validate_permissions(user, "read"):
        features.append("uploaded_files")
        features.append("database_records")
    if validate_permissions(user, "read_all_files"):
        features.append("uploaded_files_all")
    if validate_permissions(user, "add_user"):
        features.append("user_management")
    if validate_permissions(user, "set_permissions"):
        features.append("permission_management")
    return features


# /me/ endpoint
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.response import Response
from rest_framework.views import APIView


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current user info and allowed features."
    )
    def get(self, request):
        user = request.user
        features = get_allowed_features(user)
        return Response(
            {"username": user.username, "role": user.role, "features": features}
        )


class UserFeaturesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get allowed features for the current user."
    )
    def get(self, request):
        user = request.user
        features = get_allowed_features(user)
        return Response({
            "user": user.username,
            "allowed_features": features
        })


# Only keep AllowAny import
from rest_framework.permissions import AllowAny

# ABAC import
from .abac import validate_permissions
from .serializers_auth import RegisterSerializer, LoginSerializer, UserCreateSerializer

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
            return Response(
                {"token": token.key, "username": user.username, "role": user.role}
            )
        return Response(serializer.errors, status=400)


# ========== User Login =============


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=LoginSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                user = User.objects.get(email=email, password=password)
                from rest_framework.authtoken.models import Token

                token, _ = Token.objects.get_or_create(user=user)
                return Response(
                    {"token": token.key, "username": user.username, "role": user.role}
                )
            except User.DoesNotExist:
                return Response({"error": "Invalid credentials"}, status=400)
        return Response(serializer.errors, status=400)


from celery.result import AsyncResult
from rest_framework.views import APIView


from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response

from .serializers import (
    FileUploadSerializer,
    RandomUserFetchSerializer,
    PermissionAssignmentSerializer,
)

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
        ("csv", lambda c: pd.read_csv(io.BytesIO(c))),
        ("json", lambda c: pd.read_json(io.BytesIO(c))),
        ("xml", lambda c: pd.read_xml(io.BytesIO(c))),
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
      - This endpoint processes the file synchronously and saves data to MySQL table in row and column format.
      - Saves metadata to UploadedFile model.
      - Returns success message with number of rows saved.
    """

    serializer_class = FileUploadSerializer
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        # ABAC: Only allow if user has permission to upload
        user = request.user
        if not validate_permissions(user, "upload"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )

        #  Validate request (file + optional table_name)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        django_file = serializer.validated_data["file"]
        table_name = serializer.validated_data.get("table_name") or "uploaded_data"

        try:
            # Load file to dataframe
            df, fmt = load_file_to_dataframe(django_file)

            # Save dataframe to MySQL table
            df.to_sql(table_name, engine, if_exists="append", index=False)

            # Save metadata for /uploaded-files/
            UploadedFile.objects.create(
                filename=django_file.name,
                table_name=table_name,
                user=user,
                rows_added=0
            )

            return Response(
                {"message": "File uploaded successfully", "rows": len(df), "table": table_name},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FetchRandomUsersAPIView(generics.GenericAPIView):
    """
    POST /fetch-random-users/

    Triggers real-time API ingestion and
    registers it in UploadedFile list.
    """

    serializer_class = RandomUserFetchSerializer
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)

    def post(self, request, *args, **kwargs):
        user = request.user

        #  ABAC: Only allow if user has upload permission
        if not validate_permissions(user, "upload"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate input
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        count = serializer.validated_data.get("count", 2)

        try:
            from app.tasks import fetch_random_users_task

            # Trigger background task
            task = fetch_random_users_task.delay(count, user.id)

            #  REGISTER REAL-TIME API INGESTION
            UploadedFile.objects.create(
                filename="random_users_api.json",
                table_name="random_users",
                user=user,
                rows_added=count
                
            )

            return Response(
                {
                    "message": "Real-time API ingestion started",
                    "task_id": task.id,
                    "table_name": "random_users",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DatabaseRecordsAPIView(APIView):
    """
    GET /database-records/?table_name=your_table
    Allows users with 'read' access to fetch records from a MySQL table (uploaded data or flat files).
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get records from a MySQL table by table_name (requires read access)",
        manual_parameters=[
            openapi.Parameter(
                "table_name",
                openapi.IN_QUERY,
                description="MySQL table name",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
    )
    def get(self, request):
        user = request.user
        from .abac import validate_permissions

        if not validate_permissions(user, "read"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )
        table_name = request.query_params.get("table_name")
        if not table_name:
            return Response(
                {"error": "Missing table_name parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            # Use SQLAlchemy engine to fetch all data
            query = f"SELECT * FROM `{table_name}`"
            df = pd.read_sql(query, engine)
            data = df.to_dict(orient="records")
            return Response({"records": data})
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Post table_name to get records from a MySQL table (requires read access)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["table_name"],
            properties={
                "table_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Table name to fetch records from",
                )
            },
        ),
    )
    def post(self, request):
        user = request.user
        from .abac import validate_permissions

        if not validate_permissions(user, "read"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )
        table_name = request.data.get("table_name")
        if not table_name:
            return Response(
                {"error": "Missing table_name parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            query = f"SELECT * FROM `{table_name}`"
            df = pd.read_sql(query, engine)
            data = df.to_dict(orient="records")
            return Response({"records": data})
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserManagementAPIView(APIView):
    """
    GET: List all users (manager only)
    POST: Add a new user (manager only)
    DELETE: Remove a user by id (manager only)
    """

    permission_classes = [IsAuthenticated]

    def has_manager_access(self, user):
        from .abac import validate_permissions

        # Use ABAC for manager actions
        return validate_permissions(user, "add_user")

    def get(self, request):
        if not self.has_manager_access(request.user):
            return Response(
                {"error": "Access denied. Manager permission required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        from django.contrib.auth import get_user_model

        User = get_user_model()
        queryset = User.objects.all()

        # Filter users by organizations if current user has organizations
        if request.user.organizations.exists():
            queryset = queryset.filter(
                organizations__in=request.user.organizations.all()
            ).distinct()

        users = queryset.values(
            "id", "username", "email", "role", "organizations__name"
        )
        user_list = list(users)
        return Response(user_list)

    @swagger_auto_schema(request_body=UserCreateSerializer)
    def post(self, request):
        if not self.has_manager_access(request.user):
            return Response(
                {"error": "Access denied. Manager permission required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create default policy for new user
            from .models import Policy

            Policy.objects.get_or_create(
                user=user,
                defaults={
                    "can_upload": False,
                    "can_read": False,
                    "can_delete": False,
                    "can_read_all_files": False,
                    "can_add_user": False,
                    "can_delete_user": False,
                    "can_set_permissions": False,
                },
            )
            return Response(
                {
                    "message": "User created successfully",
                    "username": user.username,
                    "user_id": user.id,
                }
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a user by id (manager only)",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_QUERY,
                description="User ID to delete",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
    )
    def delete(self, request):
        # Use ABAC for delete user
        from .abac import validate_permissions

        if not validate_permissions(request.user, "delete_user"):
            return Response(
                {"error": "Access denied. Manager permission required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_id = request.query_params.get("id")
        if not user_id:
            return Response(
                {"error": "User id required"}, status=status.HTTP_400_BAD_REQUEST
            )
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({"message": "User deleted"})
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class URLFileUploadAPIView(APIView):
    """
    POST /upload-url/

    JSON payload:
      - url (required): URL of the file to upload
      - table_name (optional): MySQL table (default: uploaded_data)

    Behaviour:
      - Downloads file from URL and enqueues a Celery task to process it.
      - Returns a `task_id` which can be used to inspect results.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Upload file from URL",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["url"],
            properties={
                "url": openapi.Schema(
                    type=openapi.TYPE_STRING, description="URL of the file"
                ),
                "table_name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Table name (optional)"
                ),
            },
        ),
    )
    def post(self, request):
        user = request.user
        if not validate_permissions(user, "upload"):
            return Response(
                {"error": "Access denied by ABAC policy."},
                status=status.HTTP_403_FORBIDDEN,
            )

        url = request.data.get("url")
        table_name = request.data.get("table_name", "uploaded_data")

        if not url:
            return Response(
                {"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Download file from URL
            response = requests.get(url)
            response.raise_for_status()
            file_bytes = response.content

            from app.tasks import process_upload_task

            task = process_upload_task.delay(file_bytes, table_name, user.id)

            # Save metadata for /uploaded-files/
            UploadedFile.objects.create(
                filename=url.split('/')[-1],  # Use filename from URL
                table_name=table_name,
                user=user
            )

            return Response(
                {"message": "Task queued", "task_id": task.id},
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )   

class UserPermissionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get allowed operations for the current user."
    )
    def get(self, request):
        user = request.user
        from .abac import get_user_permissions

        permissions = get_user_permissions(user)
        allowed = [key for key, value in permissions.items() if value]

        return Response(
            {
                "username": user.username,
                "role": getattr(user, "role", None),
                "organizations": user.get_organization_names(),
                "allowed_operations": allowed,
                "permissions": permissions,
            }
        )

    @swagger_auto_schema(
        operation_description="Set allowed operations (policy) for a user (manager only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "allowed_operations"],
            properties={
                "user_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="User ID to set policy for"
                ),
                "allowed_operations": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_STRING,
                        enum=[
                            "upload",
                            "read",
                            "delete",
                            "read_all_files",
                            "add_user",
                            "delete_user",
                            "set_permissions",
                        ],
                    ),
                    description="List of allowed operations",
                ),
            },
        ),
        responses={200: openapi.Response("Policy updated")},
    )
    def post(self, request):
        user = request.user
        from .abac import validate_permissions

        if not validate_permissions(user, "set_permissions"):
            return Response(
                {"error": "Access denied. Manager permission required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_id = request.data.get("user_id")
        allowed_ops = request.data.get("allowed_operations")
        if not user_id or not isinstance(allowed_ops, list):
            return Response(
                {"error": "user_id and allowed_operations (list) required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        from .models import Policy

        User = get_user_model()
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if manager can modify this user's permissions
        if not validate_permissions(
            user, "set_permissions", {"target_user_id": user_id}
        ):
            return Response(
                {"error": "Access denied. Cannot modify this user's permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Map allowed_ops to policy fields
        policy_data = {
            "can_upload": "upload" in allowed_ops,
            "can_read": "read" in allowed_ops,
            "can_delete": "delete" in allowed_ops,
            "can_read_all_files": "read_all_files" in allowed_ops,
            "can_add_user": "add_user" in allowed_ops,
            "can_delete_user": "delete_user" in allowed_ops,
            "can_set_permissions": "set_permissions" in allowed_ops,
        }

        policy, created = Policy.objects.get_or_create(
            user=target_user, defaults=policy_data
        )
        if not created:
            for key, value in policy_data.items():
                setattr(policy, key, value)
            policy.save()

        return Response(
            {
                "message": "Policy updated",
                "user_id": user_id,
                "allowed_operations": allowed_ops,
            }
        )
