from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


# Custom User model for authentication
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('data_engineer', 'Data Engineer'),
        ('analyst', 'Analyst'),
    ]
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default='analyst')

# UploadedFile model for tracking user uploads
class UploadedFile(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	filename = models.CharField(max_length=255)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	table_name = models.CharField(max_length=255, blank=True, null=True)
	# Add more fields as needed (e.g., file_format, status, etc.)

	def __str__(self):
		return f"{self.filename} uploaded by {self.user.username}"

# Register models in admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
	fieldsets = BaseUserAdmin.fieldsets + (
		(None, {'fields': ('role',)}),
	)
	add_fieldsets = BaseUserAdmin.add_fieldsets + (
		(None, {'fields': ('role',)}),
	)
	list_display = BaseUserAdmin.list_display + ('role',)
	list_filter = BaseUserAdmin.list_filter + ('role',)

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
	list_display = ("filename", "user", "uploaded_at", "table_name")
	search_fields = ("filename", "user__username", "table_name")
