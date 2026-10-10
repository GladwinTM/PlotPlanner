from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "profiles"}
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String()), default=list)
    goals: Mapped[list[str]] = mapped_column(ARRAY(String()), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=4_000)
    interests: list[str] = Field(default_factory=list, max_length=40)
    goals: list[str] = Field(default_factory=list, max_length=20)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=4_000)
    interests: list[str] | None = Field(default=None, max_length=40)
    goals: list[str] | None = Field(default=None, max_length=20)


class ProfileRead(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="PlotPlanner Profile Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_profile(profile_id: UUID, session: AsyncSession) -> Profile:
    profile = await session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/v1/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate) -> Profile:
    async with Session.begin() as session:
        profile = Profile(**payload.model_dump())
        session.add(profile)
    return profile


@app.get("/v1/profiles/{profile_id}", response_model=ProfileRead)
async def read_profile(profile_id: UUID) -> Profile:
    async with Session() as session:
        return await get_profile(profile_id, session)


@app.patch("/v1/profiles/{profile_id}", response_model=ProfileRead)
async def update_profile(profile_id: UUID, payload: ProfileUpdate) -> Profile:
    async with Session.begin() as session:
        profile = await get_profile(profile_id, session)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
    return profile
