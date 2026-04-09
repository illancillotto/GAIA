"""Cross-dialect SQLAlchemy types for the Riordino module."""

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB


RIORDINO_UUID = Uuid
RIORDINO_JSON = JSON().with_variant(JSONB, "postgresql")
