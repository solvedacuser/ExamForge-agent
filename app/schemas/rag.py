from pydantic import BaseModel, Field


class PdfPage(BaseModel):
    source: str
    page: int = Field(ge=1)
    text: str


class DocumentChunk(BaseModel):
    id: str
    source: str
    page: int = Field(ge=1)
    text: str


class RetrievedContext(BaseModel):
    source: str
    page: int = Field(ge=1)
    text: str
    score: float
    chunk_id: str


class IndexSummary(BaseModel):
    pdf_count: int
    page_count: int
    chunk_count: int
    vector_store_path: str
