from fastapi import APIRouter

from app.api.errors import error_response
from app.rag import index_pdfs
from app.schemas.api import ErrorResponse, PdfIndexRequest, PdfIndexResponse

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])


@router.post(
    "/index",
    response_model=PdfIndexResponse,
    responses={500: {"model": ErrorResponse}},
)
def index_pdf_documents(request: PdfIndexRequest):
    try:
        summary = index_pdfs(pdf_dir=request.pdf_dir)
    except Exception:
        return error_response(
            message=(
                "PDF 인덱싱 중 문제가 발생했습니다. PDF 파일과 API Key 설정을 확인해주세요."
            ),
            status_code=500,
            error_code="pdf_index_failed",
        )

    return PdfIndexResponse(**summary.model_dump())
