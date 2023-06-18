class ChuniNetException(Exception):
    pass


class InvalidTokenException(ChuniNetException):
    pass


class MaintenanceException(ChuniNetException):
    pass


class ChuniNetError(ChuniNetException):
    def __init__(self, code: int, description: str) -> None:
        super().__init__(f"Error code {code}: {description}")
        self.code = code
        self.description = description
