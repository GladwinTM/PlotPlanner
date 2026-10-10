from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastembed import TextEmbedding
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, ForeignKey, String, Text, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Settings(BaseSettings):
    database_url: str
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False)


@lru_cache
def embedder() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": "knowledge"}
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(40))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = {"schema": "knowledge"}
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("knowledge.documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))


class DocumentCreate(BaseModel):
    profile_id: UUID
    title: str = Field(min_length=1, max_length=300)
    source_type: str = Field(pattern="^(note|resume|portfolio|job_description)$")
    source_uri: str | None = Field(default=None, max_length=2_000)
    content: str = Field(min_length=1, max_length=100_000)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    profile_id: UUID
    title: str
    source_type: str
    source_uri: str | None
    created_at: datetime
    chunk_count: int


class SearchRequest(BaseModel):
    profile_id: UUID
    query: str = Field(min_length=2, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    document_id: UUID
    document_title: str
    content: str
    score: float


def split_text(content: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Deterministic paragraph-aware chunks for initial retrieval quality."""
    words = content.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
        start += chunk_size - overlap
    return chunks


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="PlotPlanner Knowledge Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/v1/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate) -> DocumentRead:
    parts = split_text(payload.content)
    if not parts:
        raise HTTPException(status_code=422, detail="Document has no indexable content")
    vectors = list(embedder().embed(parts))
    async with Session.begin() as session:
        document = Document(**payload.model_dump(exclude={"content"}))
        session.add(document)
        await session.flush()
        session.add_all(Chunk(document_id=document.id, position=index, content=part, embedding=vector.tolist()) for index, (part, vector) in enumerate(zip(parts, vectors)))
    return DocumentRead.model_validate(document, from_attributes=True).model_copy(update={"chunk_count": len(parts)})


@app.post("/v1/search", response_model=list[SearchResult])
async def search(payload: SearchRequest) -> list[SearchResult]:
    query_vector = next(embedder().embed([payload.query])).tolist()
    distance = Chunk.embedding.cosine_distance(query_vector)
    statement = (select(Chunk, Document, distance.label("distance"))
                 .join(Document, Document.id == Chunk.document_id)
                 .where(Document.profile_id == payload.profile_id)
                 .order_by(distance).limit(payload.limit))
    async with Session() as session:
        rows = (await session.execute(statement)).all()
    return [SearchResult(document_id=document.id, document_title=document.title, content=chunk.content, score=round(1 - float(distance_value), 5)) for chunk, document, distance_value in rows]
