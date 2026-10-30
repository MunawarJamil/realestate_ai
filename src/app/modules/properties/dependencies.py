from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.properties.repository import PropertyRepository
from app.modules.properties.service import PropertyService


def get_property_service(
    session: AsyncSession = Depends(get_session),
) -> PropertyService:
    return PropertyService(repository=PropertyRepository(session))