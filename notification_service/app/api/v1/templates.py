import json
from typing import Any, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import DatabaseDep
from ...repository.template_repository import TemplateRepository
from ...schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TemplateUploadForm,
)
from ...utils.logging import setup_notification_logging

logger = setup_notification_logging("templates_api")

router = APIRouter(tags=["Templates"])


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 100,
    template_type: Optional[str] = None,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """List all notification templates"""
    repo = TemplateRepository(db)
    templates, _ = await repo.list(skip=skip, limit=limit, template_type=template_type)

    return templates


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Get a specific template by ID"""
    repo = TemplateRepository(db)
    template = await repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Update an existing template"""
    repo = TemplateRepository(db)
    template = await repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    # Check for name conflict if name is being changed
    if template_data.name and template_data.name != template.name:
        existing = await repo.get_by_name(template_data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with name '{template_data.name}' already exists",
            )

    # Process template data (handle markdown conversion)
    update_data = template_data.model_dump(exclude_unset=True)

    updated_template = await repo.update(template_id, update_data)

    return updated_template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Delete a template"""
    repo = TemplateRepository(db)
    template = await repo.get_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    await repo.delete(template_id)

    return {"message": "Template deleted successfully"}


@router.post("/upload-html", response_model=TemplateResponse)
async def upload_html_template(
    file: UploadFile = File(...),
    template_name: str = Form(...),
    email_subject: Optional[str] = Form(None),
    merge_fields: Optional[str] = Form(None),
    db: AsyncSession = DatabaseDep,
):
    """Upload an HTML file as a template"""
    repo = TemplateRepository(db)

    # Validate file type
    allowed_html_extensions = (".html", ".htm")
    if not file.filename or not file.filename.lower().endswith(allowed_html_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only HTML files are allowed ({', '.join(allowed_html_extensions)})",
        )

    # Read file content
    try:
        html_content = await file.read()
        html_content = html_content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read HTML file: {str(e)}",
        )

    # Validate form data using Pydantic model
    form_data = TemplateUploadForm(
        template_name=template_name,
        email_subject=email_subject,
        merge_fields=merge_fields,
    )

    # Check if template with same name already exists
    existing = await repo.get_by_name(form_data.template_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template with name '{form_data.template_name}' already exists",
        )

    # Parse variables if provided
    template_variables: dict[str, Any] = {}
    if form_data.merge_fields:
        try:
            template_variables = json.loads(form_data.merge_fields)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid merge fields JSON format",
            )

    # Create template using schema
    template_create = TemplateCreate(
        name=form_data.template_name,
        type="email",  # Default to email type
        content_type="text/html",
        subject=form_data.email_subject,
        body=html_content,
        variables=template_variables,
        is_active=True,
    )

    template = await repo.create(template_create.model_dump())

    logger.info(
        "HTML template uploaded successfully",
        extra={
            "template_id": template.id,
            "template_name": template.name,
            "file_size": len(html_content),
        },
    )

    return template


@router.post("/upload-text", response_model=TemplateResponse)
async def upload_text_template(
    file: UploadFile = File(...),
    template_name: str = Form(...),
    email_subject: Optional[str] = Form(None),
    merge_fields: Optional[str] = Form(None),
    db: AsyncSession = DatabaseDep,
):
    """Upload a text file as a template"""
    repo = TemplateRepository(db)

    # Validate file type
    allowed_text_extensions = (".txt", ".text", ".md", ".markdown", ".template")
    if not file.filename or not file.filename.lower().endswith(allowed_text_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only text files are allowed ({', '.join(allowed_text_extensions)})",
        )

    # Read file content
    try:
        text_content = await file.read()
        text_content = text_content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read text file: {str(e)}",
        )

    # Validate form data using Pydantic model
    form_data = TemplateUploadForm(
        template_name=template_name,
        email_subject=email_subject,
        merge_fields=merge_fields,
    )

    # Check if template with same name already exists
    existing = await repo.get_by_name(form_data.template_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template with name '{form_data.template_name}' already exists",
        )

    # Parse variables if provided
    template_variables: dict[str, Any] = {}
    if form_data.merge_fields:
        try:
            template_variables = json.loads(form_data.merge_fields)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid merge fields JSON format",
            )

    # Create template using schema
    template_create = TemplateCreate(
        name=form_data.template_name,
        type="email",  # Default to email type
        content_type="text/plain",
        subject=form_data.email_subject,
        body=text_content,
        variables=template_variables,
        is_active=True,
    )

    template = await repo.create(template_create.model_dump())

    logger.info(
        "Text template uploaded successfully",
        extra={
            "template_id": template.id,
            "template_name": template.name,
            "file_size": len(text_content),
        },
    )

    return template


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template_data: TemplateCreate,
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Create a new template"""
    repo = TemplateRepository(db)

    # Check if template with same name already exists
    existing = await repo.get_by_name(template_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template with name '{template_data.name}' already exists",
        )

    template = await repo.create(template_data.model_dump())

    logger.info(
        "Template created successfully",
        extra={
            "template_id": template.id,
            "template_name": template.name,
        },
    )

    return template
