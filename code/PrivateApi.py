#! python3

import uuid

from dataclasses import dataclass

@dataclass
class tPrivateKey:

    vIndex: str
    vToken: str

    vTimeLimit: int
    vTimeSince: int | None

    def __init__(self, vIndex: str = str(uuid.uuid4()), vTimeLimit: int = 0, vTimeSince: int | None = None):
        self.vIndex = vIndex

        self.vTimeLimit = vTimeLimit
        self.vTimeSince = vTimeSince
##### tPrivateKey
