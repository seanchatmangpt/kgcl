"""Checkpoint and restore functionality for YAWL engine.

Provides state serialization for engine, cases, and
work items to enable recovery from failures.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_engine import YEngine


class CheckpointType(Enum):
    """Type of checkpoint.

    Attributes
    ----------
    ENGINE : auto
        Full engine state
    CASE : auto
        Single case state
    WORK_ITEM : auto
        Single work item state
    INCREMENTAL : auto
        Incremental changes since last checkpoint
    """

    ENGINE = auto()
    CASE = auto()
    WORK_ITEM = auto()
    INCREMENTAL = auto()


class CheckpointStatus(Enum):
    """Status of checkpoint.

    Attributes
    ----------
    CREATED : auto
        Checkpoint created
    VALID : auto
        Checkpoint validated
    RESTORED : auto
        Checkpoint was restored
    EXPIRED : auto
        Checkpoint has expired
    CORRUPTED : auto
        Checkpoint is corrupted
    """

    CREATED = auto()
    VALID = auto()
    RESTORED = auto()
    EXPIRED = auto()
    CORRUPTED = auto()


@dataclass
class Checkpoint:
    """A checkpoint of engine or case state.

    Parameters
    ----------
    id : str
        Checkpoint ID
    checkpoint_type : CheckpointType
        Type of checkpoint
    case_id : str | None
        Case ID (for case checkpoints)
    engine_id : str | None
        Engine ID
    status : CheckpointStatus
        Current status
    created_at : datetime
        Creation timestamp
    restored_at : datetime | None
        Restoration timestamp
    state_data : dict[str, Any]
        Serialized state
    description : str
        Checkpoint description
    """

    id: str
    checkpoint_type: CheckpointType = CheckpointType.CASE
    case_id: str | None = None
    engine_id: str | None = None
    status: CheckpointStatus = CheckpointStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    restored_at: datetime | None = None
    state_data: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_json(self) -> str:
        """Serialize checkpoint to JSON.

        Returns
        -------
        str
            JSON string
        """
        return json.dumps(
            {
                "id": self.id,
                "checkpoint_type": self.checkpoint_type.name,
                "case_id": self.case_id,
                "engine_id": self.engine_id,
                "status": self.status.name,
                "created_at": self.created_at.isoformat(),
                "restored_at": self.restored_at.isoformat() if self.restored_at else None,
                "state_data": self.state_data,
                "description": self.description,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Checkpoint:
        """Deserialize checkpoint from JSON.

        Parameters
        ----------
        json_str : str
            JSON string

        Returns
        -------
        Checkpoint
            Checkpoint instance
        """
        data = json.loads(json_str)
        return cls(
            id=data["id"],
            checkpoint_type=CheckpointType[data["checkpoint_type"]],
            case_id=data.get("case_id"),
            engine_id=data.get("engine_id"),
            status=CheckpointStatus[data["status"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            restored_at=(datetime.fromisoformat(data["restored_at"]) if data.get("restored_at") else None),
            state_data=data["state_data"],
            description=data.get("description", ""),
        )


@dataclass
class CheckpointManager:
    """Manager for creating and restoring checkpoints.

    Parameters
    ----------
    checkpoints : dict[str, Checkpoint]
        Stored checkpoints by ID
    max_checkpoints : int
        Maximum checkpoints to retain
    auto_checkpoint : bool
        Whether to auto-checkpoint on major events
    """

    checkpoints: dict[str, Checkpoint] = field(default_factory=dict)
    max_checkpoints: int = 100
    auto_checkpoint: bool = True

    def create_case_checkpoint(self, case: Any, description: str = "") -> Checkpoint:
        """Create checkpoint for a case.

        Parameters
        ----------
        case : Any
            Case to checkpoint
        description : str
            Checkpoint description

        Returns
        -------
        Checkpoint
            Created checkpoint
        """
        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            checkpoint_type=CheckpointType.CASE,
            case_id=case.id,
            description=description or f"Case checkpoint: {case.id}",
            state_data=self._serialize_case(case),
        )

        self._store_checkpoint(checkpoint)
        return checkpoint

    def create_engine_checkpoint(self, engine: YEngine, description: str = "") -> Checkpoint:
        """Create checkpoint for entire engine.

        Parameters
        ----------
        engine : YEngine
            Engine to checkpoint
        description : str
            Checkpoint description

        Returns
        -------
        Checkpoint
            Created checkpoint
        """
        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            checkpoint_type=CheckpointType.ENGINE,
            engine_id=engine.engine_id,
            description=description or f"Engine checkpoint: {engine.engine_id}",
            state_data=self._serialize_engine(engine),
        )

        self._store_checkpoint(checkpoint)
        return checkpoint

    def restore_case_checkpoint(self, checkpoint_id: str, target_case: Any) -> bool:
        """Restore case from checkpoint.

        Parameters
        ----------
        checkpoint_id : str
            Checkpoint ID
        target_case : Any
            Case to restore into

        Returns
        -------
        bool
            True if restored
        """
        checkpoint = self.checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False

        if checkpoint.checkpoint_type != CheckpointType.CASE:
            return False

        try:
            self._deserialize_case(checkpoint.state_data, target_case)
            checkpoint.status = CheckpointStatus.RESTORED
            checkpoint.restored_at = datetime.now()
            return True
        except (KeyError, ValueError):
            checkpoint.status = CheckpointStatus.CORRUPTED
            return False

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Get checkpoint by ID.

        Parameters
        ----------
        checkpoint_id : str
            Checkpoint ID

        Returns
        -------
        Checkpoint | None
            Checkpoint or None
        """
        return self.checkpoints.get(checkpoint_id)

    def get_case_checkpoints(self, case_id: str) -> list[Checkpoint]:
        """Get all checkpoints for a case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        list[Checkpoint]
            Checkpoints for case
        """
        return [cp for cp in self.checkpoints.values() if cp.case_id == case_id]

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.

        Parameters
        ----------
        checkpoint_id : str
            Checkpoint ID

        Returns
        -------
        bool
            True if deleted
        """
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            return True
        return False

    def cleanup_old_checkpoints(self) -> int:
        """Remove old checkpoints beyond max.

        Returns
        -------
        int
            Number removed
        """
        if len(self.checkpoints) <= self.max_checkpoints:
            return 0

        # Sort by creation time
        sorted_cps = sorted(self.checkpoints.values(), key=lambda cp: cp.created_at)

        # Remove oldest
        to_remove = len(self.checkpoints) - self.max_checkpoints
        removed = 0
        for cp in sorted_cps[:to_remove]:
            del self.checkpoints[cp.id]
            removed += 1

        return removed

    def _store_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Store checkpoint.

        Parameters
        ----------
        checkpoint : Checkpoint
            Checkpoint to store
        """
        self.checkpoints[checkpoint.id] = checkpoint

        # Cleanup if needed
        if len(self.checkpoints) > self.max_checkpoints:
            self.cleanup_old_checkpoints()

    def _serialize_case(self, case: Any) -> dict[str, Any]:
        """Serialize case state.

        Parameters
        ----------
        case : Any
            Case to serialize

        Returns
        -------
        dict[str, Any]
            Serialized state
        """
        return {
            "id": case.id,
            "specification_id": case.specification_id,
            "status": case.status.name if hasattr(case.status, "name") else str(case.status),
            "root_net_id": case.root_net_id,
            "case_data": case.case_data,
            "work_items": [self._serialize_work_item(wi) for wi in case.work_items.values()],
            "net_runners": {net_id: self._serialize_net_runner(runner) for net_id, runner in case.net_runners.items()},
        }

    def _serialize_work_item(self, work_item: Any) -> dict[str, Any]:
        """Serialize work item.

        Parameters
        ----------
        work_item : Any
            Work item to serialize

        Returns
        -------
        dict[str, Any]
            Serialized state
        """
        return {
            "id": work_item.id,
            "case_id": work_item.case_id,
            "task_id": work_item.task_id,
            "net_id": work_item.net_id,
            "status": work_item.status.name if hasattr(work_item.status, "name") else str(work_item.status),
            "data_in": getattr(work_item, "data_in", getattr(work_item, "data_input", {})),
            "data_out": getattr(work_item, "data_out", getattr(work_item, "data_output", {})),
            "allocated_to": getattr(work_item, "allocated_to", getattr(work_item, "resource_id", None)),
            "started_by": getattr(work_item, "started_by", getattr(work_item, "resource_id", None)),
        }

    def _serialize_net_runner(self, runner: Any) -> dict[str, Any]:
        """Serialize net runner.

        Parameters
        ----------
        runner : Any
            Net runner to serialize

        Returns
        -------
        dict[str, Any]
            Serialized state
        """
        return {
            "net_id": runner.net.id,
            "case_id": runner.case_id,
            "completed": runner.completed,
            "marking": self._serialize_marking(runner.marking),
            "enabled_tasks": list(runner.get_enabled_tasks()),
        }

    def _serialize_marking(self, marking: Any) -> dict[str, Any]:
        """Serialize marking.

        Parameters
        ----------
        marking : Any
            Marking to serialize

        Returns
        -------
        dict[str, Any]
            Serialized state
        """
        return {"tokens": {place_id: count for place_id, count in marking.tokens.items()}}

    def _serialize_engine(self, engine: YEngine) -> dict[str, Any]:
        """Serialize engine state.

        Parameters
        ----------
        engine : YEngine
            Engine to serialize

        Returns
        -------
        dict[str, Any]
            Serialized state
        """
        return {
            "engine_id": engine.engine_id,
            "status": engine.status.name if hasattr(engine.status, "name") else str(engine.status),
            "specifications": list(engine.specifications.keys()),
            "cases": {case_id: self._serialize_case(case) for case_id, case in engine.cases.items()},
        }

    def _deserialize_case(self, state: dict[str, Any], target_case: Any) -> None:
        """Deserialize case state.

        Parameters
        ----------
        state : dict[str, Any]
            Serialized state
        target_case : Any
            Case to restore into
        """
        # Restore basic fields
        target_case.case_data = state.get("case_data", {})

        # Status would need to be converted from string to enum
        # This is simplified - full implementation would handle all fields

        # Restore work items would need full implementation
        # Restore net runner state would need full implementation
