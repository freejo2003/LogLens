class ExtractionError(ValueError):
    """A parser failure with a deliberately safe user-facing message."""

    def __init__(self, public_message: str):
        self.public_message = public_message
        super().__init__(public_message)


class OCRNeededError(ExtractionError):
    """The document has no text that a native parser can extract."""
