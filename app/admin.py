# Register in admin
from django.contrib import admin
from django.contrib.auth.models import User as DjangoUser, Group
try:
	admin.site.unregister(DjangoUser)
	admin.site.unregister(Group)
except Exception:
	pass


# Import models and ModelAdmin classes
from .models import Organization, User, Policy, UploadedFile, FileUpdateLog
from .models import OrganizationAdmin, UserAdmin, PolicyAdmin, UploadedFileAdmin, FileUpdateLogAdmin

# Register models with their ModelAdmin classes
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Policy, PolicyAdmin)
admin.site.register(UploadedFile, UploadedFileAdmin)
admin.site.register(FileUpdateLog, FileUpdateLogAdmin)

