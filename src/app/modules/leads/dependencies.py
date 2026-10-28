from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.leads.repository import LeadRepository
from app.modules.leads.service import LeadService


def get_lead_service(
    session: AsyncSession = Depends(get_session),
) -> LeadService:
    return LeadService(repository=LeadRepository(session))
