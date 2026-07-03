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
    workspace: Mapped[str] = mapped_column(
        String, index=True, default="default", server_default="default"
    )
    initiative_title: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(
        JSON
    )  # DecisionRecord.model_dump(mode="json")
    embedding: Mapped[list] = mapped_column(JSON)  # list[float]
    created_at: Mapped[str] = mapped_column(String)


class OutcomeRow(Base):
    __tablename__ = "memory_outcome"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace: Mapped[str] = mapped_column(
        String, index=True, default="default", server_default="default"
    )
    decision_id: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)  # OutcomeRecord.model_dump(mode="json")
    reflected_at: Mapped[str] = mapped_column(String)


class RuntimeSessionRow(Base):
    """One row per workflow execution (the Session header)."""

    __tablename__ = "runtime_session"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace: Mapped[str] = mapped_column(
        String, index=True, default="default", server_default="default"
    )
    workflow: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)


class RuntimeEventRow(Base):
    """Append-only event log for a session (the execution timeline)."""

    __tablename__ = "runtime_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String)
    ts: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)  # serialized platform Event fields


class WorkspaceConfigRow(Base):
    """One workspace-configuration value (env-shaped string) per friendly key."""

    __tablename__ = "workspace_config"

    # ponytail: PK default keeps create_all aligned with the migration's
    # server_default; R3 scopes all callers explicitly — a missing workspace=
    # writes to 'default', not an error.
    workspace: Mapped[str] = mapped_column(
        String, primary_key=True, default="default", server_default="default"
    )
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class ConnectorConfigRow(Base):
    """One raw connector config block (same shape connectors.yaml held)."""

    __tablename__ = "connector_config"

    # ponytail: PK default keeps create_all aligned with the migration's
    # server_default; R3 scopes all callers explicitly — a missing workspace=
    # writes to 'default', not an error.
    workspace: Mapped[str] = mapped_column(
        String, primary_key=True, default="default", server_default="default"
    )
    connector: Mapped[str] = mapped_column(String, primary_key=True)
    config: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[str] = mapped_column(String)


class WorkspaceRow(Base):
    """The workspace registry: one row per project/team scope."""

    __tablename__ = "workspace"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String)


class PreferenceRow(Base):
    """One user-experience preference (never affects workflow execution)."""

    __tablename__ = "preference"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
