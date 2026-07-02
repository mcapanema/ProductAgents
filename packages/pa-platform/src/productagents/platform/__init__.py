"""Application Services layer — the platform's stable, presentation-agnostic API.

Presentation adapters (TUI, CLI, IPC, GUI) depend only on this package and
``productagents.core``. They never import ``agents``, ``memory``, ``knowledge``,
or ``connectors`` directly.
"""

from productagents.platform.configuration import ConfigurationService
from productagents.platform.connector_service import ConnectorService
from productagents.platform.decision_read_service import DecisionReadService
from productagents.platform.decision_service import DecisionService
from productagents.platform.memory_service import MemoryService
from productagents.platform.preference_service import PreferenceService
from productagents.platform.prompt_service import PromptService
from productagents.platform.reflection_service import ReflectionService
from productagents.platform.session_service import SessionService
from productagents.platform.workflow import Workflow, WorkflowService
from productagents.platform.workspace import Workspace, WorkspaceService

__all__ = [
    "ConfigurationService",
    "ConnectorService",
    "DecisionReadService",
    "DecisionService",
    "MemoryService",
    "PreferenceService",
    "PromptService",
    "ReflectionService",
    "SessionService",
    "Workflow",
    "WorkflowService",
    "Workspace",
    "WorkspaceService",
]
