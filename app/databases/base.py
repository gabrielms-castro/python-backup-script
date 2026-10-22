from abc import ABC, abstractmethod


class DumpStrategy(ABC):
    """
    Generates the dump file of one database engine.
    """
    tool: str
    extension: str

    @abstractmethod
    def dump(self, output_file: str) -> bool:
        """
        Writes the dump to output_file. Returns False on failure, leaving
        no partial file behind.
        """
