"""
Data models for aggregate job metrics.

These models represent pipeline-wide daily aggregated metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from bson import ObjectId

from utils.timezone import now_utc, utc_to_local


@dataclass
class DailyAggregateMetrics:
    """Pipeline-wide daily aggregated metrics."""

    date: str  # YYYY-MM-DD
    document_type: str = "daily_aggregate"

    # MongoDB unique identifier
    _id: ObjectId | None = None

    # Pipeline health metrics
    total_companies_processed: int = 0
    companies_successful: int = 0
    companies_with_failures: int = 0
    companies_partial: int = 0
    overall_success_rate: float = 0.0

    # Data growth metrics
    total_new_jobs: int = 0
    total_jobs_deactivated: int = 0
    total_active_jobs: int = 0
    total_inactive_jobs: int = 0
    net_job_change: int = 0

    # Stage performance metrics (flat structure)
    stage_1_total_processed: int = 0
    stage_1_success_rate: float = 0.0
    stage_1_avg_execution_seconds: float = 0.0

    stage_2_total_processed: int = 0
    stage_2_success_rate: float = 0.0
    stage_2_avg_execution_seconds: float = 0.0

    stage_3_total_processed: int = 0
    stage_3_success_rate: float = 0.0
    stage_3_avg_execution_seconds: float = 0.0

    stage_4_total_processed: int = 0
    stage_4_success_rate: float = 0.0
    stage_4_avg_execution_seconds: float = 0.0

    # Metadata
    calculation_timestamp: datetime = field(default_factory=now_utc)
    pipeline_run_count: int = 0
    created_at: datetime = field(default_factory=now_utc)

    @property
    def calculation_timestamp_local(self) -> datetime:
        local_time: datetime = utc_to_local(self.calculation_timestamp)
        return local_time

    @property
    def created_at_local(self) -> datetime:
        local_time: datetime = utc_to_local(self.created_at)
        return local_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        doc = {
            "date": self.date,
            "document_type": self.document_type,
            "total_companies_processed": self.total_companies_processed,
            "companies_successful": self.companies_successful,
            "companies_with_failures": self.companies_with_failures,
            "companies_partial": self.companies_partial,
            "overall_success_rate": self.overall_success_rate,
            "total_new_jobs": self.total_new_jobs,
            "total_jobs_deactivated": self.total_jobs_deactivated,
            "total_active_jobs": self.total_active_jobs,
            "total_inactive_jobs": self.total_inactive_jobs,
            "net_job_change": self.net_job_change,
            "stage_1_total_processed": self.stage_1_total_processed,
            "stage_1_success_rate": self.stage_1_success_rate,
            "stage_1_avg_execution_seconds": self.stage_1_avg_execution_seconds,
            "stage_2_total_processed": self.stage_2_total_processed,
            "stage_2_success_rate": self.stage_2_success_rate,
            "stage_2_avg_execution_seconds": self.stage_2_avg_execution_seconds,
            "stage_3_total_processed": self.stage_3_total_processed,
            "stage_3_success_rate": self.stage_3_success_rate,
            "stage_3_avg_execution_seconds": self.stage_3_avg_execution_seconds,
            "stage_4_total_processed": self.stage_4_total_processed,
            "stage_4_success_rate": self.stage_4_success_rate,
            "stage_4_avg_execution_seconds": self.stage_4_avg_execution_seconds,
            "calculation_timestamp": self.calculation_timestamp,
            "pipeline_run_count": self.pipeline_run_count,
            "created_at": self.created_at,
        }

        # Add _id if present
        if self._id:
            doc["_id"] = self._id

        return doc

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DailyAggregateMetrics":
        """Create from dictionary."""
        return cls(
            date=data.get("date", ""),
            document_type=data.get("document_type", "daily_aggregate"),
            _id=data.get("_id"),
            total_companies_processed=data.get("total_companies_processed", 0),
            companies_successful=data.get("companies_successful", 0),
            companies_with_failures=data.get("companies_with_failures", 0),
            companies_partial=data.get("companies_partial", 0),
            overall_success_rate=data.get("overall_success_rate", 0.0),
            total_new_jobs=data.get("total_new_jobs", 0),
            total_jobs_deactivated=data.get("total_jobs_deactivated", 0),
            total_active_jobs=data.get("total_active_jobs", 0),
            total_inactive_jobs=data.get("total_inactive_jobs", 0),
            net_job_change=data.get("net_job_change", 0),
            stage_1_total_processed=data.get("stage_1_total_processed", 0),
            stage_1_success_rate=data.get("stage_1_success_rate", 0.0),
            stage_1_avg_execution_seconds=data.get(
                "stage_1_avg_execution_seconds", 0.0
            ),
            stage_2_total_processed=data.get("stage_2_total_processed", 0),
            stage_2_success_rate=data.get("stage_2_success_rate", 0.0),
            stage_2_avg_execution_seconds=data.get(
                "stage_2_avg_execution_seconds", 0.0
            ),
            stage_3_total_processed=data.get("stage_3_total_processed", 0),
            stage_3_success_rate=data.get("stage_3_success_rate", 0.0),
            stage_3_avg_execution_seconds=data.get(
                "stage_3_avg_execution_seconds", 0.0
            ),
            stage_4_total_processed=data.get("stage_4_total_processed", 0),
            stage_4_success_rate=data.get("stage_4_success_rate", 0.0),
            stage_4_avg_execution_seconds=data.get(
                "stage_4_avg_execution_seconds", 0.0
            ),
            calculation_timestamp=data.get("calculation_timestamp", now_utc()),
            pipeline_run_count=data.get("pipeline_run_count", 0),
            created_at=data.get("created_at", now_utc()),
        )
