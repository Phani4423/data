from django.urls import path
from .views import FileUploadAPIView, FetchRandomUsersAPIView, TaskStatusAPIView, RegisterAPIView, LoginAPIView, MeAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("upload/", FileUploadAPIView.as_view(), name="file-upload"),
    path("fetch-random-users/", FetchRandomUsersAPIView.as_view(), name="fetch-random-users"),
    path("task-status/<str:task_id>/", TaskStatusAPIView.as_view(), name="task-status"),
    path("me/", MeAPIView.as_view(), name="me"),
]
