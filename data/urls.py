"""
URL configuration for data project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


def get_schema_view_with_permissions():
    """Get schema view with permission-based generator"""
    from app.schema import PermissionBasedSchemaGenerator

    return get_schema_view(
        openapi.Info(
            title="ETL API Documentation",
            default_version="v1",
            description="""
            <b>Welcome to the ETL API!</b><br><br>
            <b>For Unauthenticated Users:</b><br>
            Only login and registration endpoints are visible.<br><br>
            <b>For Authenticated Users:</b><br>
            <b>Step 1:</b> You are already logged in! Your available features are shown below.<br>
            <b>Step 2:</b> Use the endpoints you have permission for based on your ABAC policies.<br><br>
            <b>Note:</b> Endpoints are filtered based on your permissions. If you don't see an endpoint, you don't have access to it.<br>
            """,
            contact=openapi.Contact(email="support@example.com"),
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
        generator_class=PermissionBasedSchemaGenerator,
    )


schema_view = get_schema_view_with_permissions()


urlpatterns = [
    path('admin/', admin.site.urls),

    # Your app URLs
    path('', include('app.urls')),

    # Swagger UI
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),

    # Redoc UI
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
]
