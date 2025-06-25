import datetime
import enum
from dataclasses import dataclass


class Direction(enum.Enum):
    IN = "IN"
    OUT = "OUT"


@dataclass
class PadMessage:
    direction: Direction
    date: datetime.datetime
    author: str
    message: str


@dataclass
class FrontexCredentials:
    token: str
    email: str
    case_id: str
    valid_until: datetime.date


@dataclass
class PadDocument:
    name: str
    link: str


@dataclass
class PadMetadata:
    created_on: datetime.datetime
    documents: list[PadDocument]
    subject: str
    created_by: str
    case_id: str


@dataclass
class PadCase:
    metadata: PadMetadata
    messages: list[PadMessage]
    raw: str
