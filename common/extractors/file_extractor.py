from __future__ import annotations

from pathlib import Path
from typing import Optional

import pdfplumber
from .base import BaseExtractor


class FileExtractor(BaseExtractor):
    """
    Extractor for local files.
    Supports: .pdf, .txt, .md
    """

    SUPPORTED_TEXT_EXTS = {".txt", ".md"}
    SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

    def extract(self, source: str) -> str:
        path = Path(source)

        if not path.exists():
            return f"[Error] File not found: {path}"

        suffix = path.suffix.lower()

        # 1. PDF Handling
        if suffix == ".pdf":
            # Hybrid Extraction: Text + OCR for pages with images
            text = extract_text_and_ocr_images_from_pdf(path)
            return text

        # 2. Image Handling
        if suffix in self.SUPPORTED_IMAGE_EXTS:
            from .google_vision_extractor import GoogleVisionExtractor
            return GoogleVisionExtractor().extract(source)

        # 3. Text Handling
        if suffix in self.SUPPORTED_TEXT_EXTS:
            return path.read_text(encoding="utf-8", errors="ignore").strip()

        return f"[Error] Unsupported file type: {suffix}"


def extract_text_with_pdfplumber(pdf_path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = (page.extract_text() or "").strip()
            if t:
                chunks.append(t)
    return "\n\n".join(chunks).strip()


def extract_text_with_pypdf(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    chunks: list[str] = []

    for page in reader.pages:
        t = (page.extract_text() or "").strip()
        if t:
            chunks.append(t)

    return "\n\n".join(chunks).strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Try pdfplumber first; if it fails OR returns empty text, fallback to pypdf.
    """
    try:
        text = extract_text_with_pdfplumber(pdf_path)
        if text:
            return text
    except Exception:
        pass

    try:
        return extract_text_with_pypdf(pdf_path)
    except Exception:
        return ""

def extract_text_and_ocr_images_from_pdf(pdf_path: Path) -> str:
    """
    Extracts text from PDF.
    Additionally, if a page contains images (larger than icon size),
    it renders the page to an image and runs Google Vision OCR to capture non-selectable text.
    """
    import pdfplumber
    import io
    from .google_vision_extractor import GoogleVisionExtractor
    
    vision = GoogleVisionExtractor()
    full_text = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                # 1. Standard Text Extraction
                page_text = (page.extract_text() or "").strip()
                if page_text:
                    full_text.append(page_text)
                
                # 2. Check for significant images
                # Filter small icons/lines (e.g. < 50x50 pixels)
                has_images = False
                if hasattr(page, 'images') and page.images:
                    for img in page.images:
                        # pdfplumber image objects have x0, y0, x1, y1 or width/height depending on version/context?
                        # actually page.images is a list of dicts: {'x0':.., 'width':..}
                        w = img.get('width', 0)
                        h = img.get('height', 0)
                        if w > 50 and h > 50:
                            has_images = True
                            break
                
                # If images found (or if page text is suspiciously empty?), run OCR
                # User asked: "If images present, unconditionally OCR".
                if has_images:
                    try:
                        # Render page to image (requires pillow)
                        # resolution=150 is usually enough for OCR
                        pil_image = page.to_image(resolution=150).original
                        
                        # Convert to bytes
                        img_byte_arr = io.BytesIO()
                        pil_image.save(img_byte_arr, format='JPEG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        ocr_text = vision.extract_bytes(img_bytes)
                        
                        if ocr_text and ocr_text.strip():
                            full_text.append(f"\n[Page {i+1} OCR Result]\n{ocr_text}\n")
                            
                    except Exception as e:
                        # Fallback simply to continue without OCR for this page
                        logger.warning(f"Failed to OCR page {i+1} of {pdf_path}: {e}")
                        
    except Exception as e:
        logger.error(f"Hybrid PDF extraction failed: {e}")
        # Fallback to simple text extraction
        return extract_text_from_pdf(pdf_path)

    return "\n\n".join(full_text).strip()
