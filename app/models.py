# Correct import order
from django.db import models
from django.contrib import admin
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Log model for file update actions
class FileUpdateLog(models.Model):
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} updated by {self.user.username} in {self.organization.name} at {self.updated_at}"


class FileUpdateLogAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "organization", "updated_at")
    search_fields = ("filename", "user__username", "organization__name")


# Organization model
class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


# Custom User model for authentication (all users are 'admin' role, but permissions are in Policy)
class User(AbstractUser):
    organizations = models.ManyToManyField(
        Organization,
        related_name='users',
        blank=True,
        help_text="Organizations this user belongs to"
    )
    role = models.CharField(
        max_length=32, default="admin"
    )  # All users are 'admin' for this scenario
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.is_staff = True
        self.is_superuser = True
        super().save(*args, **kwargs)

    def get_organization_names(self):
        """Get list of organization names for this user"""
        return list(self.organizations.values_list('name', flat=True))

    def __str__(self):
        orgs = self.get_organization_names()
        org_str = f" ({', '.join(orgs)})" if orgs else ""
        return f"{self.username}{org_str}"


# Policy model for ABAC
class Policy(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    can_upload = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_read_all_files = models.BooleanField(
        default=False, help_text="User can read all uploaded files in the database."
    )
    # Manager-specific permissions
    can_add_user = models.BooleanField(
        default=False, help_text="User can add new users (manager action)"
    )
    can_delete_user = models.BooleanField(
        default=False, help_text="User can delete users (manager action)"
    )
    can_set_permissions = models.BooleanField(
        default=False, help_text="User can set user permissions (manager action)"
    )
    # Add more permissions as needed

    def __str__(self):
        return f"Policy for {self.user.username} (upload: {self.can_upload}, read: {self.can_read}, delete: {self.can_delete})"


# UploadedFile model for tracking user uploads
class UploadedFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    rows_added = models.IntegerField(default=0)
    # Add more fields as needed (e.g., file_format, status, etc.)

    def __str__(self):
        return f"{self.filename} uploaded by {self.user.username}"


# Register models in admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "location")
    search_fields = ("name", "location")


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {"fields": ("organizations", "role")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "organizations", "role")}),
    )
    list_display = BaseUserAdmin.list_display + (
        "get_organization_names",
        "role",
    )
    list_filter = BaseUserAdmin.list_filter + (
        "organizations",
        "role",
    )


class PolicyAdmin(admin.ModelAdmin):
    list_display = ("user", "can_upload", "can_read", "can_delete")
    search_fields = ("user__username",)


class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "uploaded_at", "table_name")
    search_fields = ("filename", "user__username", "table_name")
