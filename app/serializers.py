
from rest_framework import serializers
from .models import UploadedFile


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload ETL.
    - file: uploaded file (CSV / JSON / XML / Excel)
    - table_name: optional MySQL table name
    """
    file = serializers.FileField()
    table_name = serializers.CharField(required=False, allow_blank=True)


class RandomUserFetchSerializer(serializers.Serializer):
    """
    Serializer for random user fetch API ETL.
    - count: number of random users to fetch (default: 2)
    """
    count = serializers.IntegerField(required=False, default=2, min_value=1, max_value=100)


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ("id", "filename", "uploaded_at", "table_name", "user")


class PermissionAssignmentSerializer(serializers.Serializer):
    """
    Serializer for assigning permissions to a user.
    - user_id: ID of the user to assign permissions to
    - can_upload: boolean for upload permission
    - can_read: boolean for read permission
    - can_delete: boolean for delete permission
    - can_read_all_files: boolean for read all files permission
    - can_add_user: boolean for add user permission
    - can_delete_user: boolean for delete user permission
    - can_set_permissions: boolean for set permissions permission
    """
    user_id = serializers.IntegerField()
    can_upload = serializers.BooleanField(default=False)
    can_read = serializers.BooleanField(default=False)
    can_delete = serializers.BooleanField(default=False)
    can_read_all_files = serializers.BooleanField(default=False)
    can_add_user = serializers.BooleanField(default=False)
    can_delete_user = serializers.BooleanField(default=False)
    can_set_permissions = serializers.BooleanField(default=False)
