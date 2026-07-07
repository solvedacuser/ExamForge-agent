from pathlib import Path

from pypdf import PdfReader

from app.schemas.rag import PdfPage


def load_pdf_pages(pdf_path: Path) -> list[PdfPage]:
    reader = PdfReader(str(pdf_path))
    pages: list[PdfPage] = []

    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        normalized_text = " ".join(text.split())
        if normalized_text:
            pages.append(
                PdfPage(
                    source=pdf_path.name,
                    page=page_index,
                    text=normalized_text,
                )
            )

    return pages


def load_pdfs_from_directory(pdf_dir: str) -> list[PdfPage]:
    directory = Path(pdf_dir)
    if not directory.exists():
        return []

    pages: list[PdfPage] = []
    for pdf_path in sorted(directory.glob("*.pdf")):
        pages.extend(load_pdf_pages(pdf_path))

    return pages
