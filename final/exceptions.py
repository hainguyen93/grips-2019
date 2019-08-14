# Python user-defined exceptions


class CLArgumentsNotMatch(Exception):
    """Raised when command-line arguments do not match"""
    pass


class DayNotFound(Exception):
    """Raised when a selected day is not found"""
    pass
