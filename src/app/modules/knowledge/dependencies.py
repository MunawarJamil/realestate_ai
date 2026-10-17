from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.integrations.qdrant.client import get_qdrant
from app.modules.knowledge.repository import KnowledgeDocumentRepository
from app.modules.knowledge.service import KnowledgeService
from app.modules.knowledge.storage import FileStorage, build_file_storage
from app.modules.knowledge.vector_store import ChunkVectorStore
from app.workers.queue import get_ingestion_queue
from app.integrations.embeddings.client import get_embedding_client
from app.modules.knowledge.retrieval import RetrievalService

@lru_cache
def get_file_storage() -> FileStorage:
    return build_file_storage()


def get_knowledge_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> KnowledgeService:
    return KnowledgeService(
        repository=KnowledgeDocumentRepository(session),
        storage=get_file_storage(),
        store=ChunkVectorStore(get_qdrant(), settings.qdrant_collection),
        queue=get_ingestion_queue(),
        max_upload_bytes=settings.max_upload_bytes,
    )


def get_retrieval_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RetrievalService:
    return RetrievalService(
        embedder=get_embedding_client(),
        store=ChunkVectorStore(get_qdrant(), settings.qdrant_collection),
        repository=KnowledgeDocumentRepository(session),
        default_limit=settings.retrieval_top_k,
        score_threshold=settings.retrieval_score_threshold,
    )