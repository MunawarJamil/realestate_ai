import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    allowed_domains: list[str] = Field(default_factory=list)

    # Initial Agency Admin Credentials (Optional upon provisioning)
    admin_email: EmailStr | None = None
    admin_full_name: str | None = None
    admin_password: str | None = Field(default=None, min_length=8)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    allowed_domains: list[str] | None = None
    is_active: bool | None = None


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    api_key_prefix: str
    widget_key: str
    allowed_domains: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime


class TenantCreated(TenantRead):
    api_key: str  # raw key, only in response
    admin_email: str | None = None
    admin_password: str | None = None  # returned once upon creation for initial handoff
