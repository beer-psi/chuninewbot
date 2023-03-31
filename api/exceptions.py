class ChuniNetException(Exception):
    pass


class InvalidTokenException(ChuniNetException):
    pass


class MaintenanceException(ChuniNetException):
    pass
