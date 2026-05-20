import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.types import TypeDecorator, UserDefinedType

from app.core.database import Base


class _TSVectorType(TypeDecorator):
    """
    TSVECTOR su PostgreSQL, TEXT su SQLite (per i test in-memory).
    Non usare direttamente: usare il simbolo `TSVector` sotto.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class WikiChunk(Base):
    """
    Frammento di documento indicizzato.
    Retrieval: search_vector (PostgreSQL FTS con GIN index).
    In test SQLite: search_vector è TEXT nullable, la query FTS è mockata.
    """

    __tablename__ = "wiki_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file = Column(String(512), nullable=False, index=True)
    section_title = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    search_vector = Column(_TSVectorType, nullable=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WikiRequest(Base):
    """Richiesta utente: feature non implementata o domanda senza risposta."""

    __tablename__ = "wiki_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_question = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, default="feature_request")
    status = Column(String(32), nullable=False, default="pending")
    created_by = Column(String(256), nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
