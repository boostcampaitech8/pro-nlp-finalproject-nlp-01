from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """Abstract Base Class for all portfolio extractors."""
    
    @abstractmethod
    def extract(self, source: str) -> str:
        """
        Extracts text from the given source.
        
        Args:
            source (str): The path or URL to the source.
            
        Returns:
            str: The extracted raw text.
        """
        pass
