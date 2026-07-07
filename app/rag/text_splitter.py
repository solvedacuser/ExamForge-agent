from app.schemas.rag import DocumentChunk, PdfPage


def split_pages(
    pages: list[PdfPage],
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[DocumentChunk] = []

    for page in pages:
        start = 0
        chunk_index = 1

        while start < len(page.text):
            end = min(start + chunk_size, len(page.text))
            chunk_text = page.text[start:end].strip()

            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        id=f"{page.source}:p{page.page}:c{chunk_index}",
                        source=page.source,
                        page=page.page,
                        text=chunk_text,
                    )
                )

            if end == len(page.text):
                break

            start = end - chunk_overlap
            chunk_index += 1

    return chunks
