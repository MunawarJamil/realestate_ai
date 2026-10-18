from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.integrations.llm.base import LLMProvider
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService
from app.modules.knowledge.dependencies import get_retrieval_service
from app.modules.knowledge.retrieval import RetrievalService


def get_llm_client(request: Request) -> LLMProvider:
    return request.app.state.llm_client  # type: ignore[no-any-return]


def get_chat_service(
    session: AsyncSession = Depends(get_session),
    retrieval: RetrievalService = Depends(get_retrieval_service),
    llm: LLMProvider = Depends(get_llm_client),
) -> ChatService:
    return ChatService(
        repository=ChatRepository(session),
        retrieval=retrieval,
        llm=llm,
    )
