"""
Prefect tasks for the job processing pipeline.

This module contains individual tasks that can be orchestrated
by Prefect flows to process job data with proper monitoring,
error handling, and retry capabilities.
"""

from pipeline.tasks.stage_1_task import process_job_listings_task
from pipeline.tasks.stage_2_task import process_job_details_task
from pipeline.tasks.stage_3_task import process_job_skills_task
from pipeline.tasks.stage_4_task import process_job_technologies_task
from pipeline.tasks.stage_5_task import upload_jobs_to_supabase_task
from pipeline.tasks.sync_companies_task import sync_companies_task

__all__ = [
    "process_job_details_task",
    "process_job_listings_task",
    "process_job_skills_task",
    "process_job_technologies_task",
    "sync_companies_task",
    "upload_jobs_to_supabase_task",
]
