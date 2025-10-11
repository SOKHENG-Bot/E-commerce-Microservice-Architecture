from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TemplateBase(BaseModel):
    name: str
    type: str  # email, sms, push
    content_type: str = "text/plain"  # text/plain, text/html
    subject: Optional[str] = None
    body: Optional[str] = None
    markdown_body: Optional[str] = None  # Alternative to body for easier editing
    variables: Optional[dict[str, Any]] = {}
    is_active: bool = True


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
