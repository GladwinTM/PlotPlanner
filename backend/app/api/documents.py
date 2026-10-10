from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import LLM, CurrentUser, Session, rate_limited
from app.schemas.profile import FactRead
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    processing_status: str
    error: str | None
    created_at: datetime
    processed_at: datetime | None


class DocumentDetail(DocumentRead):
    text_preview: str | None
    text_length: int
    facts: list[FactRead]


async def _detail(session, user_id: UUID, document_id: UUID) -> DocumentDetail:
    document = await document_service.get_document(session, user_id, document_id, with_text=True)
    facts = await document_service.document_facts(session, user_id, document_id)
    text = document.extracted_text or ""
    return DocumentDetail(
        **DocumentRead.model_validate(document).model_dump(),
        text_preview=text[:3000] or None, text_length=len(text),
        facts=[FactRead.model_validate(f) for f in facts],
    )


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED, dependencies=[rate_limited("upload", per_minute=5)])
async def upload_document(file: UploadFile, request: Request, user: CurrentUser, session: Session, llm: LLM):
    max_bytes = request.app.state.settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    document = await document_service.upload(session, llm, user.id, file.filename or "document", data, max_bytes)
    return await _detail(session, user.id, document.id)


@router.get("", response_model=list[DocumentRead])
async def list_documents(user: CurrentUser, session: Session):
    return await document_service.list_documents(session, user.id)


@router.get("/{document_id}", response_model=DocumentDetail)
async def read_document(document_id: UUID, user: CurrentUser, session: Session):
    return await _detail(session, user.id, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, user: CurrentUser, session: Session, keep_confirmed_facts: bool = True):
    await document_service.delete_document(session, user.id, document_id, keep_confirmed_facts=keep_confirmed_facts)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
