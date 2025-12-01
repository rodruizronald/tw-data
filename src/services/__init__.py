"""
Service layer for the job pipeline.

This module contains service classes that handle specific aspects of the pipeline:
- HTML extraction from web pages
- OpenAI API interactions
- Database operations for pipeline stages
- Job metrics collection and aggregation
- Web page parsing strategies
- Company management through external API
"""

from services.data_service import JobDataService
from services.metrics_service import JobMetricsService, job_metrics_service
from services.supabase_service import SupabaseService

__all__ = [
    "CompanyService",
    "JobDataService",
    "JobMetricsService",
    "SupabaseService",
    "job_metrics_service",
]
