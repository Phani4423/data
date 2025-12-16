# abac.py
# Simple ABAC engine for your project

ABAC_POLICIES = [
    {"role": "data_engineer", "resource_type": "file", "actions": ["ingest", "transform", "load"]},
    {"role": "data_engineer", "resource_type": "api", "actions": ["ingest", "validate"]},
    {"role": "admin", "resource_type": "file", "actions": ["all"]},
    {"role": "admin", "resource_type": "api", "actions": ["all"]},
    {"role": "analyst", "resource_type": "file", "actions": ["read"]},
    # analyst denied for api
]

def abac_check(user_role, action, resource_attrs):
    for policy in ABAC_POLICIES:
        if (policy["role"] == user_role and
            policy["resource_type"] == resource_attrs["resource_type"] and
            (action in policy["actions"] or "all" in policy["actions"])):
            return True
    return False
