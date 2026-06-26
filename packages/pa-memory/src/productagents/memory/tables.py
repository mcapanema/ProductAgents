"""The pa-memory schema: a dedicated SQLAlchemy metadata, independent of the
canonical store's ``SQLModel.metadata`` so this subsystem owns its own tables,
migrations, and Alembic version history while sharing the same database file.

Both records store their full pydantic payload verbatim as JSON (byte-stable
round-trip, like the canonical store); the decision row also carries the
initiative embedding so retrieval needs no re-embedding of history.
"""

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """pa-memory's own declarative base (separate metadata from pa-knowledge)."""


class DecisionRow(Base):
    __tablename__ = "memory_decision"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    initiative_title: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(
        JSON
    )  # DecisionRecord.model_dump(mode="json")
    embedding: Mapped[list] = mapped_column(JSON)  # list[float]
    created_at: Mapped[str] = mapped_column(String)


class OutcomeRow(Base):
    __tablename__ = "memory_outcome"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)  # OutcomeRecord.model_dump(mode="json")
    reflected_at: Mapped[str] = mapped_column(String)
