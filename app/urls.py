from django.urls import path
from .views import FileUploadAPIView,FetchCarDataAPIView

urlpatterns = [
    path("upload/", FileUploadAPIView.as_view(), name="file-upload"),
    path("fetch-cars/", FetchCarDataAPIView.as_view(), name="fetch-cars"),
]
