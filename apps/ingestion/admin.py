from django.contrib import admin

from .models import SourceFile


@admin.register(SourceFile)
class SourceFileAdmin(admin.ModelAdmin):
    list_display = (
        "original_name",
        "workspace",
        "owner",
        "extension",
        "byte_size",
        "extraction_status",
        "uploaded_at",
    )
    search_fields = (
        "original_name",
        "checksum",
        "owner__username",
        "workspace__name",
    )
    list_filter = (
        "extension",
        "extraction_status",
        "uploaded_at",
    )