from enum import Enum


class Actions(Enum):
    ACCESS = ("access", "access")
    NO_ACCESS = ("no_access", "not access")
    GET = ("get", "get")
    LIST = ("list", "list")
    FILTER = ("filter", "filter")
    HISTORY = ("history", "get the history of")
    IDENTIFY = ("identify", "identify values from")
    ADD = ("add", "add")
    CHANGE = ("change", "change")
    DELETE = ("delete", "delete")

    def __init__(self, label: str, description: str) -> None:
        self.label = label
        self.description = description
