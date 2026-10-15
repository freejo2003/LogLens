from django.conf import settings
from django.db import models

from apps.workspaces.models import Workspace


class SourceFile(models.Model):
    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        OCR_NEEDED = "ocr_needed", "OCR Needed"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="source_files",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="source_files",
    )

    original_name = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    storage_path = models.CharField(max_length=1000)

    extension = models.CharField(max_length=20)
    detected_type = models.CharField(max_length=100)
    text_encoding = models.CharField(max_length=40, blank=True)
    byte_size = models.BigIntegerField()

    checksum = models.CharField(max_length=64)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    extraction_status = models.CharField(
        max_length=20,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING,
    )
    extraction_error = models.CharField(max_length=255, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)

    retention_until = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["owner", "-uploaded_at"]),
            models.Index(fields=["workspace", "extraction_status"]),
        ]

    def __str__(self):
        return self.original_name


class TextSegment(models.Model):
    source_file = models.ForeignKey(
        SourceFile,
        on_delete=models.CASCADE,
        related_name="text_segments",
    )

    sequence = models.PositiveIntegerField()

    text = models.TextField()

    page_number = models.PositiveIntegerField(null=True, blank=True)
    paragraph_number = models.PositiveIntegerField(null=True, blank=True)
    line_number = models.PositiveIntegerField(null=True, blank=True)

    section_label = models.CharField(max_length=255, blank=True)

    parser_name = models.CharField(max_length=100)
    parser_version = models.CharField(max_length=50, blank=True)

    extraction_warning = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_file", "sequence"],
                name="unique_source_file_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["source_file", "sequence"]),
        ]

    def __str__(self):
        return f"{self.source_file.original_name} — segment {self.sequence}"
