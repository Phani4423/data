from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ("username", "password", "role")

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            role=validated_data.get("role", "analyst")
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "role", "organization")

class UserCreateSerializer(serializers.Serializer):
    username = serializers.RegexField(
        regex=r'^[\w.@+-]+$',
        max_length=150,
        min_length=1,
        required=True,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    email = serializers.EmailField(required=True, help_text="Required. Must be a valid email address.")
    password = serializers.CharField(write_only=True, min_length=1, required=True, help_text="Password")
    role = serializers.CharField(max_length=32, min_length=1, required=True, help_text="Role")
    organization_id = serializers.IntegerField(required=True, help_text="Organization ID")

    def create(self, validated_data):
        User = get_user_model()
        org_id = validated_data.pop('organization_id')
        from app.models import Organization
        organization = Organization.objects.get(id=org_id)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role']
        )
        user.organizations.add(organization)
        return user
