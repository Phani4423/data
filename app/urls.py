from django.urls import path
from .views import FileUploadAPIView, FetchRandomUsersAPIView, TaskStatusAPIView, RegisterAPIView, LoginAPIView, MeAPIView, UserFeaturesAPIView, UploadedFileListAPIView, DatabaseRecordsAPIView, UserManagementAPIView, UserPermissionsAPIView # Import UserManagementAPIView and UserPermissionsAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("upload/", FileUploadAPIView.as_view(), name="file-upload"),
    path("fetch-random-users/", FetchRandomUsersAPIView.as_view(), name="fetch-random-users"),
    path("task-status/<str:task_id>/", TaskStatusAPIView.as_view(), name="task-status"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("my-features/", UserFeaturesAPIView.as_view(), name="my-features"),
    path("uploaded-files/", UploadedFileListAPIView.as_view(), name="uploaded-files"),
    path("database-records/", DatabaseRecordsAPIView.as_view(), name="database-records"),  # New endpoint
    path("user-management/", UserManagementAPIView.as_view(), name="user-management"),  # Manager user management actions
    path("user-permissions/", UserPermissionsAPIView.as_view(), name="user-permissions"),  # New endpoint for user permissions
]
