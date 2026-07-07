import json
import math
from pathlib import Path

from pydantic import BaseModel

from app.schemas.rag import DocumentChunk, RetrievedContext


class VectorRecord(BaseModel):
    chunk: DocumentChunk
    embedding: list[float]


class LocalVectorStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def save(self, records: list[VectorRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.model_dump() for record in records]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> list[VectorRecord]:
        if not self.path.exists():
            return []

        raw_records = json.loads(self.path.read_text(encoding="utf-8"))
        return [VectorRecord.model_validate(record) for record in raw_records]

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedContext]:
        records = self.load()
        scored_records = [
            (_cosine_similarity(query_embedding, record.embedding), record)
            for record in records
        ]
        scored_records.sort(key=lambda item: item[0], reverse=True)

        return [
            RetrievedContext(
                source=record.chunk.source,
                page=record.chunk.page,
                text=record.chunk.text,
                score=score,
                chunk_id=record.chunk.id,
            )
            for score, record in scored_records[:top_k]
        ]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return dot_product / (left_norm * right_norm)
