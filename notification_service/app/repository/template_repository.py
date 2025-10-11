from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.template import Template


class TemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, template_data: Dict[str, Any]) -> Template:
        """Create a new template"""
        template = Template(**template_data)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: int) -> Optional[Template]:
        """Get template by ID"""
        result = await self.db.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Template]:
        """Get template by name"""
        result = await self.db.execute(select(Template).where(Template.name == name))
        return result.scalar_one_or_none()

    async def list(
        self, skip: int = 0, limit: int = 100, template_type: Optional[str] = None
    ) -> tuple[List[Template], int]:
        """List templates with optional filtering and total count"""
        query = select(Template)

        if template_type:
            query = query.where(Template.type == template_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        templates = list(result.scalars().all())

        return templates, total

    async def update(
        self, template_id: int, template_data: Dict[str, Any]
    ) -> Optional[Template]:
        """Update template"""
        await self.db.execute(
            update(Template).where(Template.id == template_id).values(**template_data)
        )
        await self.db.commit()

        # Return updated template
        return await self.get_by_id(template_id)

    async def delete(self, template_id: int) -> bool:
        """Delete template"""
        result = await self.db.execute(
            delete(Template).where(Template.id == template_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def save_file_to_db(
        self, name: str, file_path: str, file_content: str, file_format: str
    ) -> Optional[Template]:
        """Save file content to database"""
        # Check if template already exists
        existing = await self.get_by_name(name)
        if existing:
            # Update existing template
            update_data = {
                "file_path": file_path,
                "file_content": file_content,
                "file_format": file_format,
            }
            return await self.update(existing.id, update_data)

        # Create new template with file data
        template_data = {
            "name": name,
            "type": "email",  # Default type
            "content_type": "text/html",
            "subject": f"{name.replace('_', ' ').title()}",
            "body": "",  # Will be populated from file content
            "file_path": file_path,
            "file_content": file_content,
            "file_format": file_format,
        }
        return await self.create(template_data)

    async def get_file_from_db(self, name: str) -> Optional[Dict[str, Any]]:
        """Get file content from database"""
        template = await self.get_by_name(name)
        if template and template.file_content:
            return {
                "name": template.name,
                "file_path": template.file_path,
                "file_content": template.file_content,
                "file_format": template.file_format,
            }
        return None
