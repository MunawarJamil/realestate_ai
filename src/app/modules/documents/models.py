import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.documents.enums import DocumentStatus


def _document_status_values(enum_cls: type[DocumentStatus]) -> list[str]:
    return [m.value for m in enum_cls]


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        # Same tenant should not be able to upload same file twice (content based dedupe)
        UniqueConstraint("tenant_id", "checksum_sha256", name="uq_documents_tenant_checksum"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Location of the file in the storage backend (local path or S3 key), not the absolute path
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)

    # Non-native enum: Postgres ENUM type migrations are painful, so we use VARCHAR
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            native_enum=False,
            length=20,
            values_callable=_document_status_values,
        ),
        default=DocumentStatus.PENDING,
        server_default=DocumentStatus.PENDING.value,
        index=True,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # "metadata" SQLAlchemy ka reserved attribute hai, isliye attribute ka naam metadata_ hai
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )