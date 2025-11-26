"""
Data models for daily job metrics.

These models represent daily metrics for individual companies in the job scraping pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from bson import ObjectId

from utils.timezone import now_utc, utc_to_local


@dataclass
class StageMetrics:
    """Metrics for a specific pipeline stage."""

    status: str  # success|failed|skipped
    jobs_processed: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    execution_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = {
            "status": self.status,
            "jobs_processed": self.jobs_processed,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "execution_seconds": self.execution_seconds,
        }

        if self.started_at:
            data["started_at"] = self.started_at
        if self.completed_at:
            data["completed_at"] = self.completed_at
        if self.error_message:
            data["error_message"] = self.error_message

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageMetrics":
        """Create from dictionary."""
        return cls(
            status=data.get("status", "unknown"),
            jobs_processed=data.get("jobs_processed", 0),
            jobs_completed=data.get("jobs_completed", 0),
            jobs_failed=data.get("jobs_failed", 0),
            execution_seconds=data.get("execution_seconds", 0.0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
        )


@dataclass
class CompanyDailyMetrics:
    """Daily metrics for a single company's pipeline run."""

    # Required fields (no defaults) - must come first
    date: str  # YYYY-MM-DD
    company_name: str

    # Optional fields with defaults
    document_type: str = "company_daily"

    # MongoDB unique identifier
    _id: ObjectId | None = None

    # Company-level metrics
    new_jobs_found: int = 0
    total_active_jobs: int = 0
    total_inactive_jobs: int = 0
    jobs_deactivated_today: int = 0
    overall_status: str = "pending"  # success|partial|failed|pending

    # Stage 1 metrics (flat fields matching MongoDB storage)
    stage_1_status: str | None = None
    stage_1_jobs_processed: int = 0
    stage_1_jobs_completed: int = 0
    stage_1_jobs_failed: int = 0
    stage_1_execution_seconds: float = 0.0
    stage_1_started_at: datetime | None = None
    stage_1_completed_at: datetime | None = None
    stage_1_error_message: str | None = None

    # Stage 2 metrics (flat fields matching MongoDB storage)
    stage_2_status: str | None = None
    stage_2_jobs_processed: int = 0
    stage_2_jobs_completed: int = 0
    stage_2_jobs_failed: int = 0
    stage_2_execution_seconds: float = 0.0
    stage_2_started_at: datetime | None = None
    stage_2_completed_at: datetime | None = None
    stage_2_error_message: str | None = None

    # Stage 3 metrics (flat fields matching MongoDB storage)
    stage_3_status: str | None = None
    stage_3_jobs_processed: int = 0
    stage_3_jobs_completed: int = 0
    stage_3_jobs_failed: int = 0
    stage_3_execution_seconds: float = 0.0
    stage_3_started_at: datetime | None = None
    stage_3_completed_at: datetime | None = None
    stage_3_error_message: str | None = None

    # Stage 4 metrics (flat fields matching MongoDB storage)
    stage_4_status: str | None = None
    stage_4_jobs_processed: int = 0
    stage_4_jobs_completed: int = 0
    stage_4_jobs_failed: int = 0
    stage_4_execution_seconds: float = 0.0
    stage_4_started_at: datetime | None = None
    stage_4_completed_at: datetime | None = None
    stage_4_error_message: str | None = None

    # Metadata
    prefect_flow_run_id: str | None = None
    pipeline_version: str | None = None
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    last_updated_stage: str | None = None

    @property
    def created_at_local(self) -> datetime:
        local_time: datetime = utc_to_local(self.created_at)
        return local_time

    @property
    def updated_at_local(self) -> datetime:
        local_time: datetime = utc_to_local(self.updated_at)
        return local_time

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to flat dictionary structure for MongoDB storage.

        All stage metrics are already flat in the model, so this is a
        straightforward conversion to dict.
        """
        doc = {
            "date": self.date,
            "company_name": self.company_name,
            "document_type": self.document_type,
            "new_jobs_found": self.new_jobs_found,
            "total_active_jobs": self.total_active_jobs,
            "total_inactive_jobs": self.total_inactive_jobs,
            "jobs_deactivated_today": self.jobs_deactivated_today,
            "overall_status": self.overall_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        # Add _id if present
        if self._id:
            doc["_id"] = self._id

        # Add optional metadata fields
        if self.prefect_flow_run_id:
            doc["prefect_flow_run_id"] = self.prefect_flow_run_id
        if self.pipeline_version:
            doc["pipeline_version"] = self.pipeline_version
        if self.last_updated_stage:
            doc["last_updated_stage"] = self.last_updated_stage

        # Add all stage metrics (already flat in the model)
        for stage_num in range(1, 5):
            # Add status if present
            status = getattr(self, f"stage_{stage_num}_status")
            if status is not None:
                doc[f"stage_{stage_num}_status"] = status

            # Add numeric fields (always include, even if 0)
            doc[f"stage_{stage_num}_jobs_processed"] = getattr(
                self, f"stage_{stage_num}_jobs_processed"
            )
            doc[f"stage_{stage_num}_jobs_completed"] = getattr(
                self, f"stage_{stage_num}_jobs_completed"
            )
            doc[f"stage_{stage_num}_jobs_failed"] = getattr(
                self, f"stage_{stage_num}_jobs_failed"
            )
            doc[f"stage_{stage_num}_execution_seconds"] = getattr(
                self, f"stage_{stage_num}_execution_seconds"
            )

            # Add datetime fields if present
            started_at = getattr(self, f"stage_{stage_num}_started_at")
            if started_at is not None:
                doc[f"stage_{stage_num}_started_at"] = started_at

            completed_at = getattr(self, f"stage_{stage_num}_completed_at")
            if completed_at is not None:
                doc[f"stage_{stage_num}_completed_at"] = completed_at

            error_message = getattr(self, f"stage_{stage_num}_error_message")
            if error_message is not None:
                doc[f"stage_{stage_num}_error_message"] = error_message

        return doc

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyDailyMetrics":
        """
        Create from flat dictionary structure.

        Since the model is now flat, this directly maps fields from the dict.
        """
        # Extract stage metrics fields with proper type handling
        stage_fields: dict[str, Any] = {}
        for stage_num in range(1, 5):
            stage_fields[f"stage_{stage_num}_status"] = data.get(
                f"stage_{stage_num}_status"
            )
            stage_fields[f"stage_{stage_num}_jobs_processed"] = data.get(
                f"stage_{stage_num}_jobs_processed", 0
            )
            stage_fields[f"stage_{stage_num}_jobs_completed"] = data.get(
                f"stage_{stage_num}_jobs_completed", 0
            )
            stage_fields[f"stage_{stage_num}_jobs_failed"] = data.get(
                f"stage_{stage_num}_jobs_failed", 0
            )
            stage_fields[f"stage_{stage_num}_execution_seconds"] = data.get(
                f"stage_{stage_num}_execution_seconds", 0.0
            )
            stage_fields[f"stage_{stage_num}_started_at"] = data.get(
                f"stage_{stage_num}_started_at"
            )
            stage_fields[f"stage_{stage_num}_completed_at"] = data.get(
                f"stage_{stage_num}_completed_at"
            )
            stage_fields[f"stage_{stage_num}_error_message"] = data.get(
                f"stage_{stage_num}_error_message"
            )

        return cls(
            date=data.get("date", ""),
            company_name=data.get("company_name", ""),
            document_type=data.get("document_type", "company_daily"),
            _id=data.get("_id"),
            new_jobs_found=data.get("new_jobs_found", 0),
            total_active_jobs=data.get("total_active_jobs", 0),
            total_inactive_jobs=data.get("total_inactive_jobs", 0),
            jobs_deactivated_today=data.get("jobs_deactivated_today", 0),
            overall_status=data.get("overall_status", "pending"),
            prefect_flow_run_id=data.get("prefect_flow_run_id"),
            pipeline_version=data.get("pipeline_version"),
            created_at=data.get("created_at", now_utc()),
            updated_at=data.get("updated_at", now_utc()),
            last_updated_stage=data.get("last_updated_stage"),
            **stage_fields,
        )
