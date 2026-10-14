from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import analyst_required

from apps.ingestion.forms import SourceFileUploadForm
from apps.ingestion.models import SourceFile
from apps.ingestion.services.deletion import delete_source_file
from apps.ingestion.services.extraction import process_source_file
from apps.ingestion.services.storage import (
    calculate_sha256,
    delete_private_file,
    generate_storage_key,
    save_private_file,
)


@login_required
@analyst_required
def upload_source_file(request):
    if request.method == "POST":
        form = SourceFileUploadForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            workspace = form.cleaned_data["workspace"]

            extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
            extension = f".{extension}"

            checksum = calculate_sha256(uploaded_file)
            storage_key = generate_storage_key(extension)
            storage_path = save_private_file(
                uploaded_file,
                storage_key,
            )

            try:
                with transaction.atomic():
                    source_file = SourceFile.objects.create(
                        workspace=workspace,
                        owner=request.user,
                        original_name=uploaded_file.name,
                        storage_key=storage_key,
                        storage_path=storage_path,
                        extension=extension,
                        detected_type=(
                            uploaded_file.content_type
                            or "application/octet-stream"
                        ),
                        byte_size=uploaded_file.size,
                        checksum=checksum,
                        extraction_status=(
                            SourceFile.ExtractionStatus.PENDING
                        ),
                    )
            except Exception:
                delete_private_file(storage_path)
                raise

            messages.success(
                request,
                (
                    f"'{source_file.original_name}' was uploaded "
                    f"successfully. File ID: {source_file.id}. "
                    "Status: Pending extraction."
                ),
            )

            return redirect("ingestion:upload")

    else:
        form = SourceFileUploadForm(user=request.user)

    source_files = (
        SourceFile.objects
        .filter(owner=request.user)
        .select_related("workspace")
        .order_by("-uploaded_at")
    )

    return render(
        request,
        "ingestion/upload.html",
        {
            "form": form,
            "source_files": source_files,
        },
    )


@login_required
@analyst_required
def extract_source_file(request, source_file_id):
    if request.method != "POST":
        return redirect("ingestion:upload")

    source_file = get_object_or_404(
        SourceFile,
        id=source_file_id,
        owner=request.user,
    )

    if (
        source_file.extraction_status
        == SourceFile.ExtractionStatus.SUCCEEDED
    ):
        messages.info(
            request,
            f"'{source_file.original_name}' has already been extracted.",
        )
        return redirect("ingestion:upload")

    try:
        segment_count = process_source_file(source_file)

        messages.success(
            request,
            (
                f"'{source_file.original_name}' was extracted "
                f"successfully. {segment_count} text segment(s) created."
            ),
        )

    except Exception as exc:
        messages.error(
            request,
            f"Extraction failed for '{source_file.original_name}': {exc}",
        )

    return redirect("ingestion:upload")


@login_required
@analyst_required
def delete_source_file_view(request, source_file_id):
    if request.method != "POST":
        return redirect("ingestion:upload")

    source_file = get_object_or_404(
        SourceFile,
        id=source_file_id,
        owner=request.user,
    )

    file_name = source_file.original_name

    try:
        delete_source_file(
            source_file=source_file,
            owner=request.user,
        )

    except PermissionError:
        messages.error(
            request,
            "You do not have permission to delete this file.",
        )
        return redirect("ingestion:upload")

    except ValueError:
        messages.error(
            request,
            "The file could not be deleted because its storage path is invalid.",
        )
        return redirect("ingestion:upload")

    messages.success(
        request,
        f"'{file_name}' was deleted successfully.",
    )

    return redirect("ingestion:upload")