"""Deterministic stage-level recall diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class RecallStage(str, Enum):
    EXTRACTION = "EXTRACTION"
    RAW_ACTIVATION = "RAW_ACTIVATION"
    ACTIVATION_GATE = "ACTIVATION_GATE"
    RECALL_SELECTION = "RECALL_SELECTION"
    EXTERNAL_ADMISSION = "EXTERNAL_ADMISSION"
    WORKING_MEMORY = "WORKING_MEMORY"
    REVEAL_POLICY = "REVEAL_POLICY"


@dataclass(frozen=True)
class DiagnosticEvent:
    sequence: int
    stage: RecallStage
    identifier: str
    accepted: bool
    reason: str
    input_score: float | None = None
    output_score: float | None = None
    fatigue_contribution: float = 0.0
    activation_source: str = ""
    selected_thread_group: str = ""
    raw_frequency: int = 0
    reinforcement_contribution: float = 0.0
    source_trace: str = ""
    connection: str = ""
    destination: str = ""
    final_selected: bool | None = None
    expected_hit_contribution: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["stage"] = self.stage.value
        return value


class DiagnosticRecorder:
    """Optional in-memory recorder; omitting it has no behavioural effect."""

    def __init__(self) -> None:
        self.events: list[DiagnosticEvent] = []

    def record(self, stage: RecallStage, identifier: str, accepted: bool, reason: str, **values: Any) -> DiagnosticEvent:
        if not reason.strip():
            raise ValueError("diagnostic reason must not be empty")
        event = DiagnosticEvent(len(self.events) + 1, stage, identifier, accepted, reason, **values)
        self.events.append(event)
        return event

    def to_jsonable(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]
