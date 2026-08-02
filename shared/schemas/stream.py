from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StreamMessageType(str, Enum):
    STATE = "state"
    RESULT = "result"


class StateEvent(BaseModel):
    """A full state snapshot pushed from the server to every subscriber."""

    type: StreamMessageType = StreamMessageType.STATE
    data: dict[str, Any] = Field(default_factory=dict)


class Command(BaseModel):
    """An action a client asks the server to run over the state stream."""

    action: str
    id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class CommandResult(BaseModel):
    """The server's reply to a single `Command`, correlated by its id."""

    type: StreamMessageType = StreamMessageType.RESULT
    ok: bool
    id: str | None = None
    action: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
