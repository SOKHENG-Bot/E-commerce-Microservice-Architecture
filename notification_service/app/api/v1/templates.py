import json
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.deps import DatabaseDep
from ...repository.template_repository import TemplateRepository
from ...schemas.template import TemplateResponse, TemplateUpdate
from ...utils.logging import setup_notification_logging

logger = setup_notification_logging("templates_api")

router = APIRouter(prefix="/templates", tags=["templates"])


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
    name: Optional[str] = None,
    type: str = "email",
    subject: Optional[str] = None,
    variables: Optional[str] = None,  # JSON string of variables
    correlation_id: Optional[str] = None,
    db: AsyncSession = DatabaseDep,
):
    """Upload an HTML file as a template"""
    repo = TemplateRepository(db)

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".html"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTML files are allowed",
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

    # Use filename as template name if not provided
    if not name:
        name = (
            file.filename.replace(".html", "")
            .replace("_", " ")
            .title()
            .replace(" ", "_")
            .lower()
        )

    # Check if template with same name already exists
    existing = await repo.get_by_name(name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template with name '{name}' already exists",
        )

    # Parse variables if provided
    template_variables = {}
    if variables:
        try:
            template_variables = json.loads(variables)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid variables JSON format",
            )

    # Create template data
    template_data = {
        "name": name,
        "type": type,
        "content_type": "text/html",
        "subject": subject,
        "body": html_content,
        "variables": template_variables,
        "is_active": True,
    }

    template = await repo.create(template_data)

    logger.info(
        "HTML template uploaded successfully",
        extra={
            "template_id": template.id,
            "template_name": template.name,
            "file_size": len(html_content),
            "correlation_id": correlation_id,
        },
    )

    return template
