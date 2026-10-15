import codecs

from django.conf import settings

from apps.ingestion.models import TextSegment
from apps.ingestion.services.errors import ExtractionError


class SegmentBatchWriter:
    """Insert extracted segments in bounded batches and enforce text limits."""

    def __init__(self, source_file: object, *, batch_size: int = 500):
        self.source_file = source_file
        self.batch_size = batch_size
        self.sequence = 0
        self.character_count = 0
        self._batch = []

    def add(self, text: str, **locator) -> None:
        self.character_count += len(text)
        self.sequence += 1
        if self.character_count > settings.MAX_EXTRACTED_CHARACTERS:
            raise ExtractionError("The extracted text exceeds the configured size limit.")
        if self.sequence > settings.MAX_TEXT_SEGMENTS:
            raise ExtractionError("The document contains too many text segments to process.")
        self._batch.append(
            TextSegment(
                source_file=self.source_file,
                sequence=self.sequence,
                text=text,
                **locator,
            )
        )
        if len(self._batch) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if self._batch:
            TextSegment.objects.bulk_create(self._batch, batch_size=self.batch_size)
            self._batch.clear()

    def finish(self) -> int:
        self.flush()
        return self.sequence


def iter_decoded_lines(file_obj, encoding: str, *, chunk_size: int = 64 * 1024):
    """Decode incrementally so a huge, unbroken line stays within the text cap."""
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    buffer = ""

    def pop_lines(final: bool = False):
        nonlocal buffer
        while True:
            newline_positions = [
                position
                for position in (buffer.find("\n"), buffer.find("\r"))
                if position >= 0
            ]
            if not newline_positions:
                return
            position = min(newline_positions)
            if buffer[position] == "\r" and position + 1 == len(buffer) and not final:
                return
            consumed = position + 1
            if buffer[position] == "\r" and buffer[position:position + 2] == "\r\n":
                consumed += 1
            line = buffer[:position]
            buffer = buffer[consumed:]
            yield line

    while chunk := file_obj.read(chunk_size):
        buffer += decoder.decode(chunk)
        yield from pop_lines()
        if len(buffer) > settings.MAX_EXTRACTED_CHARACTERS:
            raise ExtractionError("A single extracted text line exceeds the configured size limit.")

    buffer += decoder.decode(b"", final=True)
    yield from pop_lines(final=True)
    if buffer:
        yield buffer
