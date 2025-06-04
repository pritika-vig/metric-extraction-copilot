from enum import Enum


class ResponseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    DEGRADED = "DEGRADED"
