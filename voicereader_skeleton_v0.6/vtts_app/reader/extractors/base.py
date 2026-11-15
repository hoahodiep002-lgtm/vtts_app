from typing import Protocol


class Extractor(Protocol):
    def extract(self, path: str) -> str: ...
