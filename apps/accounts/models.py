from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        WORKSPACE_CREATED = "workspace.created", "Workspace created"
        ROLE_ASSIGNED = "role.assigned", "Application role assigned"
        EXPORT_CREATED = "export.created", "Report or search export created"
        FILE_UPLOADED = "file.uploaded", "Source file uploaded"
        EXTRACTION_COMPLETED = "extraction.completed", "Extraction completed"
        EXTRACTION_FAILED = "extraction.failed", "Extraction failed"
        FILE_DELETED = "file.deleted", "Source file deleted"
        SEARCH_COMPLETED = "search.completed", "Search completed"
        SEARCH_FAILED = "search.failed", "Search failed"
        SAVED_SEARCH_CREATED = "saved_search.created", "Saved search created"
        INDICATOR_RULE_CREATED = "indicator_rule.created", "Indicator rule created"
        INDICATOR_RULE_UPDATED = "indicator_rule.updated", "Indicator rule updated"
        BENCHMARK_COMPLETED = "benchmark.completed", "Benchmark completed"
        BENCHMARK_FAILED = "benchmark.failed", "Benchmark failed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=80, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} — {self.object_type} {self.object_id}"
