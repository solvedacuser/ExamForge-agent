from fastapi import APIRouter

from app.memory import get_session_memory
from app.schemas.api import SessionStateResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=SessionStateResponse)
def get_session_state(session_id: str) -> SessionStateResponse:
    memory = get_session_memory(session_id=session_id)
    return SessionStateResponse(**memory.model_dump())
