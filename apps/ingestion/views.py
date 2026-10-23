import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import analyst_required
from apps.accounts.audit import record_event
from apps.accounts.models import AuditEvent
from apps.ingestion.forms import SourceFileUploadForm
from apps.ingestion.models import SourceFile
from apps.ingestion.services.deletion import delete_source_file
from apps.ingestion.services.storage import (
    calculate_sha256,
    delete_private_file,
    generate_storage_key,
    save_private_file,
)
from apps.ingestion.tasks import enqueue_extraction


logger = logging.getLogger(__name__)


@login_required
@analyst_required
def upload_source_file(request):
    if request.method == "POST":
        form = SourceFileUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            for name, error in form.upload_errors:
                messages.error(request, f"{name}: {error}")

            workspace = form.cleaned_data["workspace"]
            for uploaded_file in form.cleaned_data["files"]:
                storage_key = generate_storage_key(uploaded_file.loglens_extension)
                storage_path = ""
                try:
                    checksum = calculate_sha256(uploaded_file)
                    storage_path = save_private_file(uploaded_file, storage_key)
                    with transaction.atomic():
                        source_file = SourceFile.objects.create(
                            workspace=workspace,
                            owner=request.user,
                            original_name=uploaded_file.loglens_display_name,
                            storage_key=storage_key,
                            storage_path=storage_path,
                            extension=uploaded_file.loglens_extension,
                            detected_type=uploaded_file.loglens_detected_type,
                            text_encoding=uploaded_file.loglens_encoding,
                            byte_size=uploaded_file.size,
                            checksum=checksum,
                            extraction_status=SourceFile.ExtractionStatus.PENDING,
                        )
                        record_event(
                            actor=request.user,
                            workspace=workspace,
                            action=AuditEvent.Action.FILE_UPLOADED,
                            object_type="SourceFile",
                            object_id=source_file.pk,
                            details={"extension": source_file.extension, "byte_size": source_file.byte_size},
                        )
                        enqueue_extraction(source_file.pk)
                    messages.success(
                        request,
                        f"'{source_file.original_name}' was uploaded and queued for extraction.",
                    )
                except Exception as exc:
                    if storage_path:
                        try:
                            delete_private_file(storage_path)
                        except (OSError, ValueError) as cleanup_exc:
                            logger.error(
                                "Rejected upload cleanup failed for user id=%s error_type=%s",
                                request.user.pk,
                                type(cleanup_exc).__name__,
                            )
                    logger.error(
                        "Upload could not be stored for user id=%s error_type=%s",
                        request.user.pk,
                        type(exc).__name__,
                    )
                    messages.error(
                        request,
                        f"'{uploaded_file.loglens_display_name}' could not be saved. Please try again.",
                    )
            return redirect("ingestion:upload")
    else:
        form = SourceFileUploadForm(user=request.user)

    source_files = (
        SourceFile.objects.filter(owner=request.user)
        .select_related("workspace")
        .order_by("-uploaded_at")
    )
    active_extractions = source_files.filter(
        extraction_status__in=[
            SourceFile.ExtractionStatus.PENDING,
            SourceFile.ExtractionStatus.PROCESSING,
        ]
    ).count()
    return render(
        request,
        "ingestion/upload.html",
        {
            "form": form,
            "source_files": source_files,
            "active_extractions": active_extractions,
        },
    )


@login_required
@analyst_required
@require_POST
def extract_source_file(request, source_file_id):
    source_file = get_object_or_404(
        SourceFile, id=source_file_id, owner=request.user
    )
    if source_file.extraction_status == SourceFile.ExtractionStatus.SUCCEEDED:
        messages.info(request, f"'{source_file.original_name}' has already been extracted.")
    elif source_file.extraction_status == SourceFile.ExtractionStatus.PROCESSING:
        messages.info(request, f"'{source_file.original_name}' is already being extracted.")
    else:
        source_file.extraction_status = SourceFile.ExtractionStatus.PENDING
        source_file.extraction_error = ""
        source_file.processing_started_at = None
        source_file.save(
            update_fields=["extraction_status", "extraction_error", "processing_started_at"]
        )
        enqueue_extraction(source_file.pk)
        messages.success(request, f"Extraction was queued for '{source_file.original_name}'.")
    return redirect("ingestion:upload")


@login_required
@analyst_required
@require_POST
def delete_source_file_view(request, source_file_id):
    source_file = get_object_or_404(
        SourceFile, id=source_file_id, owner=request.user
    )
    file_name = source_file.original_name
    try:
        delete_source_file(source_file=source_file, owner=request.user)
    except PermissionError:
        messages.error(request, "You do not have permission to delete this file.")
    except ValueError:
        messages.error(request, "The file could not be deleted because its storage path is invalid.")
    except OSError:
        messages.error(request, "The file records were removed, but its private copy could not be purged.")
    else:
        messages.success(request, f"'{file_name}' and its extracted results were deleted.")
    return redirect("ingestion:upload")
