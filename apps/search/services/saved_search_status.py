from dataclasses import dataclass


@dataclass(frozen=True)
class SavedSearchSourceStatus:
    status: str
    message: str


CURRENT = "current"
CHANGED = "changed"
MISSING = "missing"


def get_saved_search_source_status(saved_search):
    source_file = saved_search.source_file

    if source_file is None:
        return SavedSearchSourceStatus(
            status=MISSING,
            message="The saved search has no associated source file.",
        )

    if not saved_search.source_checksum:
        return SavedSearchSourceStatus(
            status=CHANGED,
            message="The saved search has no source checksum snapshot.",
        )

    if source_file.checksum != saved_search.source_checksum:
        return SavedSearchSourceStatus(
            status=CHANGED,
            message="The source file has changed since this search was saved.",
        )

    return SavedSearchSourceStatus(
        status=CURRENT,
        message="The source file matches the saved-search snapshot.",
    )