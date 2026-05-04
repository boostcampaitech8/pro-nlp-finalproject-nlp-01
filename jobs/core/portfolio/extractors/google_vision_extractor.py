import os
import base64
import logging
import httpx
from typing import Optional
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class GoogleVisionExtractor(BaseExtractor):
    """
    Extractor using Google Cloud Vision API for OCR.
    Supports images and (indirectly via conversion) PDF pages.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.api_url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"

    def extract(self, source: str) -> str:
        """
        Extracts text from an image file path.
        """
        if not self.api_key:
            logger.error("GOOGLE_API_KEY for Vision API is not set.")
            return "[Error] Vision API key missing"

        try:
            with open(source, "rb") as image_file:
                content = base64.b64encode(image_file.read()).decode("utf-8")

            payload = {
                "requests": [
                    {
                        "image": {"content": content},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }
                ]
            }

            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()

            # Extract full text
            full_text = ""
            responses = data.get("responses", [])
            if responses:
                full_text = responses[0].get("fullTextAnnotation", {}).get("text", "")

            return full_text.strip()

        except Exception as e:
            logger.error(f"Google Vision OCR failed: {e}")
            return f"[Error] Vision OCR failure: {e}"

    def extract_bytes(self, image_bytes: bytes) -> str:
        """
        Extracts text from image bytes directly.
        """
        if not self.api_key:
            return "[Error] Vision API key missing"

        try:
            content = base64.b64encode(image_bytes).decode("utf-8")
            
            payload = {
                "requests": [
                    {
                        "image": {"content": content},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }
                ]
            }

            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()

            full_text = ""
            responses = data.get("responses", [])
            if responses:
                full_text = responses[0].get("fullTextAnnotation", {}).get("text", "")

            return full_text.strip()

        except Exception as e:
            logger.error(f"Google Vision OCR (Bytes) failed: {e}")
            return ""
            
    def extract_from_pdf_pages(self, pdf_path: str) -> str:
        """
        For serverless-friendly PDF OCR, we would ideally convert PDF to images.
        However, since we have pdfplumber/pypdf for text-based extraction,
        this will be used as a fallback for scanned PDFs.
        """
        # Note: True PDF OCR usually requires converting pages to images (e.g., using pdf2image/poppler).
        # But poppler is hard to pack in serverless.
        # Alternatively, Google Vision API can handle PDF/TIFF directly on GCS.
        # For local files, we'll try to extract what we can or advise the user.
        return self.extract(pdf_path) # Direct image extraction for now
