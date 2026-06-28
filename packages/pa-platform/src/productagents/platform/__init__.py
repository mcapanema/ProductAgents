"""Application Services layer — the platform's stable, presentation-agnostic API.

Presentation adapters (TUI, CLI, IPC, GUI) depend only on this package and
``productagents.core``. They never import ``agents``, ``memory``, ``knowledge``,
or ``connectors`` directly.
"""

from productagents.platform.connector_service import ConnectorService
from productagents.platform.decision_service import DecisionService
from productagents.platform.session_service import SessionService

__all__ = ["ConnectorService", "DecisionService", "SessionService"]
