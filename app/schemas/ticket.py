
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


def validate_not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be blank")
    return value


class TicketCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Literal["low", "medium", "high"] = "medium"

    _validate_title = field_validator("title")(validate_not_blank)
    _validate_description = field_validator("description")(validate_not_blank)


class TicketUpdate(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)

    _validate_title = field_validator("title")(validate_not_blank)
    _validate_description = field_validator("description")(validate_not_blank)


class MessageCreate(BaseModel):
    message: str = Field(min_length=1)

    _validate_message = field_validator("message")(validate_not_blank)


class AssignTicket(BaseModel):
    support_id: int = Field(gt=0)


class StatusUpdate(BaseModel):
    status: Literal["in_progress", "resolved"]


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    status: str
    owner_id: int
    assigned_to: int | None

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
