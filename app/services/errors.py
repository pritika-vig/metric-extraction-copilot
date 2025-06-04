from dataclasses import dataclass
from typing import Optional


class ProjectServiceError(Exception):
    """Base class for all service layer errors."""

    def message(self) -> str:
        raise NotImplementedError


@dataclass
class NotFoundError(ProjectServiceError):
    resource: str
    resource_id: Optional[str] = None

    def message(self) -> str:
        return f"{self.resource} not found" + (f": {self.resource_id}" if self.resource_id else "")


@dataclass
class NotAuthorizedError(ProjectServiceError):
    action: str
    resource: Optional[str] = None

    def message(self) -> str:
        base = "Not authorized"
        if self.resource:
            base += f" to {self.action} {self.resource}"
        else:
            base += f" to {self.action}"
        return base


@dataclass
class InternalServiceError(ProjectServiceError):
    detail: str

    def message(self) -> str:
        return f"Internal error: {self.detail}"
