from enum import Enum

class MessageType(str, Enum):
    TEXT    = "text"
    FORM    = "form"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"
