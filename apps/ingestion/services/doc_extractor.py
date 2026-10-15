import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.errors import ExtractionError
from apps.ingestion.services.segment_writer import SegmentBatchWriter, iter_decoded_lines
from apps.ingestion.services.validators import validate_text_file


DOC_PARSER_NAME = "libreoffice"
DOC_PARSER_VERSION = "1.0"


def extract_doc_file(source_file: SourceFile) -> int:
    if source_file.extension != ".doc":
        raise ExtractionError("This legacy Word parser does not support the uploaded file type.")

    source_path = Path(source_file.storage_path)
    if not source_path.exists() or not source_path.is_file():
        raise ExtractionError("The original upload is unavailable. Upload the file again.")

    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        raise ExtractionError(
            "Legacy DOC conversion requires LibreOffice. Use the provided container or convert the file to DOCX."
        )

    TextSegment.objects.filter(source_file=source_file).delete()

    with tempfile.TemporaryDirectory(prefix="loglens-doc-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        output_directory = temporary_path / "output"
        profile_directory = temporary_path / "profile"
        output_directory.mkdir()
        profile_directory.mkdir()
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(temporary_path),
            "TMPDIR": str(temporary_path),
            "LANG": "C.UTF-8",
        }
        command = [
            executable,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--norestore",
            f"-env:UserInstallation={profile_directory.as_uri()}",
            "--convert-to",
            "txt:Text",
            "--outdir",
            str(output_directory),
            str(source_path),
        ]
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=settings.DOC_CONVERSION_TIMEOUT,
                check=False,
                close_fds=True,
                env=environment,
                start_new_session=(os.name == "posix"),
            )
        except subprocess.TimeoutExpired as exc:
            raise ExtractionError("Legacy DOC conversion exceeded its time limit.") from exc
        except OSError as exc:
            raise ExtractionError("Legacy DOC conversion could not be started.") from exc

        converted_path = output_directory / f"{source_path.stem}.txt"
        if result.returncode != 0 or not converted_path.is_file():
            raise ExtractionError("The legacy DOC could not be converted. Verify that it is a valid Word document.")

        try:
            with converted_path.open("rb") as converted_file:
                encoding = validate_text_file(converted_file)
            writer = SegmentBatchWriter(source_file)
            with converted_path.open("rb") as converted_file:
                for line_number, line in enumerate(
                    iter_decoded_lines(converted_file, encoding), start=1
                ):
                    writer.add(
                        line,
                        line_number=line_number,
                        parser_name=DOC_PARSER_NAME,
                        parser_version=DOC_PARSER_VERSION,
                    )
            return writer.finish()
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError("The converted DOC text could not be processed safely.") from exc
