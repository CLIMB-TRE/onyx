from enum import Enum


class Actions(Enum):
    ACCESS = ("access", "access")
    NO_ACCESS = ("no_access", "no access")
    GET = ("get", "get a record from")
    LIST = ("list", "list records from")
    FILTER = ("filter", "filter records from")
    HISTORY = ("history", "get a record's history from")
    IDENTIFY = ("identify", "identify a value from")
    ADD = ("add", "add a record to")
    CHANGE = ("change", "change a record on")
    DELETE = ("delete", "delete a record on")

    def __init__(self, label: str, description: str) -> None:
        self.label = label
        self.description = description
