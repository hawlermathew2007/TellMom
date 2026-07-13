from enum import Enum


class ResponseStatus(str, Enum):
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
