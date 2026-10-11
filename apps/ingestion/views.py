from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from apps.ingestion.forms import SourceFileUploadForm
from apps.ingestion.models import SourceFile
from apps.ingestion.services.storage import (
    calculate_sha256,
    generate_storage_key,
    save_private_file,
)


@login_required
def upload_source_file(request):
    if request.method == "POST":
        form = SourceFileUploadForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            workspace = form.cleaned_data["workspace"]

            extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
            extension = f".{extension}"

            checksum = calculate_sha256(uploaded_file)
            storage_key = generate_storage_key(extension)

            with transaction.atomic():
                storage_path = save_private_file(
                    uploaded_file,
                    storage_key,
                )

                SourceFile.objects.create(
                    workspace=workspace,
                    owner=request.user,
                    original_name=uploaded_file.name,
                    storage_key=storage_key,
                    storage_path=storage_path,
                    extension=extension,
                    detected_type=uploaded_file.content_type
                    or "application/octet-stream",
                    byte_size=uploaded_file.size,
                    checksum=checksum,
                    extraction_status=SourceFile.ExtractionStatus.PENDING,
                )

            return redirect("ingestion:upload")

    else:
        form = SourceFileUploadForm(user=request.user)

    return render(
        request,
        "ingestion/upload.html",
        {"form": form},
    )