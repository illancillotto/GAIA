import logging
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.wiki.models import WikiChunk
from app.modules.wiki.schemas import WikiArticleGroup, WikiArticleSummary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wiki"])


def _is_browsable_article(source_file: str) -> bool:
    return source_file.lower().endswith(".md")


@router.get("/articles", response_model=list[WikiArticleGroup])
def list_articles(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> list[WikiArticleGroup]:
    """Lista degli articoli indicizzati, raggruppati per source_file."""
    chunks = (
        db.query(WikiChunk)
        .filter(WikiChunk.source_file.like("%.md"))
        .order_by(WikiChunk.source_file, WikiChunk.chunk_index)
        .all()
    )

    grouped: dict[str, list[WikiChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.source_file].append(chunk)

    return [
        WikiArticleGroup(
            source_file=source_file,
            chunks=[
                WikiArticleSummary(
                    source_file=c.source_file,
                    section_title=c.section_title,
                    excerpt=c.content[:300],
                    chunk_index=c.chunk_index,
                )
                for c in file_chunks
            ],
        )
        for source_file, file_chunks in sorted(grouped.items())
    ]


@router.get("/articles/{source_file:path}", response_model=WikiArticleGroup)
def get_article(
    source_file: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> WikiArticleGroup:
    """Restituisce tutti i chunk di un documento specifico."""
    chunks = (
        db.query(WikiChunk)
        .filter(WikiChunk.source_file == source_file)
        .order_by(WikiChunk.chunk_index)
        .all()
    )

    if not _is_browsable_article(source_file):
        chunks = []

    return WikiArticleGroup(
        source_file=source_file,
        chunks=[
            WikiArticleSummary(
                source_file=c.source_file,
                section_title=c.section_title,
                excerpt=c.content,  # contenuto completo per la visualizzazione
                chunk_index=c.chunk_index,
            )
            for c in chunks
        ],
    )
