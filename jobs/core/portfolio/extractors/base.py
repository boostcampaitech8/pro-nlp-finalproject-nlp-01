from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, source: str) -> str:
        """
        source: File path, URL, or Notion Page ID
        Returns: Extracted raw text
        """
        pass
