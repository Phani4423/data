# app/schema.py
from drf_yasg.generators import OpenAPISchemaGenerator
from .views import get_allowed_features


class PermissionBasedSchemaGenerator(OpenAPISchemaGenerator):

    def get_endpoints(self, request):
        endpoints = super().get_endpoints(request)

        # 🔓 Unauthenticated users → only login & register
        if not request or not request.user.is_authenticated:
            return {
                path: methods
                for path, methods in endpoints.items()
                if "login" in path or "register" in path
            }

        user = request.user
        allowed_features = get_allowed_features(user)

        # ✅ Feature names MUST match get_allowed_features()
        feature_endpoint_map = {
            "update_platform_files": ["upload"],
            "fetch_random_users": ["fetch-random-users"],
            "uploaded_files": ["uploaded-files"],
            "database_records": ["database-records"],
            "user_management": ["user-management"],
            "permission_management": ["user-permissions"],
        }

        always_allowed = ["me", "my-features", "task-status"]

        filtered = {}

        for path, methods in endpoints.items():
            # Always visible endpoints
            if any(x in path for x in always_allowed):
                filtered[path] = methods
                continue

            # Permission-based endpoints
            for feature in allowed_features:
                if feature in feature_endpoint_map:
                    if any(x in path for x in feature_endpoint_map[feature]):
                        filtered[path] = methods
                        break

        return filtered
