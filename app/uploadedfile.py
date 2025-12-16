from django.conf import settings
from django.db import models

class UploadedFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    # Add more fields as needed (e.g., file_format, status, etc.)

    def __str__(self):
        return f"{self.filename} uploaded by {self.user.username}"
