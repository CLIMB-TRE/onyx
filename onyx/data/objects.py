from enum import Enum


class OnyxObject(Enum):
    RECORD = (
        "record",
        "records",
    )
    ANALYSIS = (
        "analysis",
        "analyses",
    )

    def __init__(self, label: str, plural: str) -> None:
        self.label = label
        self.plural = plural
