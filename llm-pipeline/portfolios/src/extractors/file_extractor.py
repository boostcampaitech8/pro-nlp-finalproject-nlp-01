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

    def extract(self, source: str) -> str:
        path = Path(source)

        if not path.exists():
            return f"[Error] File not found: {path}"

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            text = extract_text_from_pdf(path)
            return text

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


def build_txt_in_background(pdf_path: Path, txt_path: Path) -> None:
    """
    Optional utility: extract text and write it to txt_path.
    (This is not required by the pipeline, but can be useful for caching / debugging.)
    """
    try:
        text = extract_text_from_pdf(pdf_path)
        if not text:
            text = "[추출된 텍스트가 없습니다. (스캔 PDF면 OCR이 필요할 수 있어요)]"
    except Exception as e:
        text = f"[텍스트 추출 실패]\n{type(e).__name__}: {e}"

    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(text, encoding="utf-8")
