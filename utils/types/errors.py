class ChuniBotError(Exception):
    """Base class for all bot exceptions."""


class MissingDetailedParams(ChuniBotError):
    """Raised when a record is missing params for accessing details."""

    def __init__(self) -> None:
        super().__init__("Cannot fetch song details if song.detailed is None.")
