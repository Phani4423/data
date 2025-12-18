# abac.py
# ABAC engine using Policy model from database with organization-based access
from app.models import Policy


# action: 'upload', 'read', 'delete', etc.
# resource: optional dict with resource attributes like {'organization': org_id, 'user_id': user_id}
def validate_permissions(user, action, resource=None):
    
    try:
        policy = Policy.objects.get(user=user)
    except Policy.DoesNotExist:
        return False

    # Check basic permissions
    if action == "upload":
        permission = policy.can_upload
    elif action == "read":
        permission = policy.can_read
    elif action == "delete":
        permission = policy.can_delete
    elif action == "read_all_files":
        permission = getattr(policy, "can_read_all_files", False)
    elif action == "add_user":
        permission = getattr(policy, "can_add_user", False)
    elif action == "delete_user":
        permission = getattr(policy, "can_delete_user", False)
    elif action == "set_permissions":
        permission = getattr(policy, "can_set_permissions", False)
    else:
        return False

    if not permission:
        return False

    # Organization-based access control
    if resource:
        # Check organization access for resources
        if 'organization' in resource:
            # User can only access resources in their organizations
            user_org_ids = list(user.organizations.values_list('id', flat=True))
            if resource['organization'] not in user_org_ids:
                return False

        # Check user-specific access (e.g., for permission assignment)
        if 'target_user_id' in resource:
            target_user_id = resource['target_user_id']
            # Only allow managers to modify other users' permissions
            if target_user_id != user.id and not getattr(policy, "can_set_permissions", False):
                return False

    return True


def get_user_permissions(user):
    """
    Get all permissions for a user as a dictionary.

    Args:
        user: User instance

    Returns:
        dict: Dictionary of user permissions
    """
    try:
        policy = Policy.objects.get(user=user)
        return {
            'can_upload': policy.can_upload,
            'can_read': policy.can_read,
            'can_delete': policy.can_delete,
            'can_read_all_files': getattr(policy, "can_read_all_files", False),
            'can_add_user': getattr(policy, "can_add_user", False),
            'can_delete_user': getattr(policy, "can_delete_user", False),
            'can_set_permissions': getattr(policy, "can_set_permissions", False),
        }
    except Policy.DoesNotExist:
        return {
            'can_upload': False,
            'can_read': False,
            'can_delete': False,
            'can_read_all_files': False,
            'can_add_user': False,
            'can_delete_user': False,
            'can_set_permissions': False,
        }
