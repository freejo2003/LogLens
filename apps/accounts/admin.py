from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User

from apps.accounts.models import AuditEvent


admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(User)
class LogLensUserAdmin(UserAdmin):
    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), "groups")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "workspace", "action", "object_type", "object_id")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "object_type", "object_id")
    readonly_fields = ("actor", "workspace", "action", "object_type", "object_id", "details", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
