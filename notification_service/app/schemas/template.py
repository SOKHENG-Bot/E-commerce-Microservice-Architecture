import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateBase(BaseModel):
    name: str
    type: str  # email, sms, push
    content_type: str = "text/html"  # text/plain, text/html
    subject: Optional[str] = None
    body: Optional[str] = None
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


class TemplateUploadForm(BaseModel):
    """Pydantic model for template upload form data"""

    template_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    email_subject: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
    )
    merge_fields: Optional[str] = Field(
        None,
    )

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        if v:
            # Convert to lowercase and replace spaces with underscores
            return v.lower().replace(" ", "_")
        return v

    @field_validator("merge_fields")
    @classmethod
    def validate_merge_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                # Validate that it's valid JSON
                parsed = json.loads(v)
                if not isinstance(parsed, dict):
                    raise ValueError(
                        "Merge fields must be a JSON object with field names and example values"
                    )
                return v
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for merge fields: {str(e)}")
        return v
