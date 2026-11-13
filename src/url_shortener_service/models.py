import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.url_shortener_service.database import Base


class Tier(str, enum.Enum):
    FREE = "Free"
    PREMIUM = "Premium"
    ADMIN = "Admin"


url_tags = Table(
    "url_tags",
    Base.metadata,
    Column("url_id", ForeignKey("urls.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    tier: Mapped[Tier] = mapped_column(Enum(Tier), default=Tier.FREE)
    urls: Mapped[list[URL]] = relationship(back_populates="owner")


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_url: Mapped[str] = mapped_column(String, nullable=False)
    short_code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    custom_alias: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    favicon: Mapped[str | None] = mapped_column(String, nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    owner: Mapped[User] = relationship(back_populates="urls")
    clicks: Mapped[list[Click]] = relationship(back_populates="url")
    tags: Mapped[list[Tag]] = relationship(secondary=url_tags, back_populates="urls")


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id", ondelete="CASCADE"))
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    referrer: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[URL] = relationship(back_populates="clicks")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    urls: Mapped[list[URL]] = relationship(secondary=url_tags, back_populates="tags")
