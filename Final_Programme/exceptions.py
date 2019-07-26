# Python user-defined exceptions

class CommandLineArguments(Exception):
   """Raised when command-line arguments do not match"""
   pass

class DayNotFound(Exception):
    """Raised when a selected day is not found"""
    pass
