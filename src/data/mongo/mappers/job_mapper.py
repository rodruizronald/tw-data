"""
Mappers for converting between domain models and database models.

This module provides bidirectional mapping between the Job model (domain model)
and JobListing model (database model) following the mapper pattern.
"""

from core.models.jobs import (
    Job,
    JobDetails,
    JobRequirements,
    JobTechnologies,
    Technology,
)
from data.mongo.models.job_listing import JobListing, TechnologyInfo


class JobMapper:
    """
    Mapper for converting between Job (domain model) and JobListing (database model).

    Provides static methods for bidirectional conversion while handling
    data transformation and validation.
    """

    @staticmethod
    def to_job_listing(job: Job) -> JobListing:
        """
        Convert Job domain model to JobListing database model.

        Args:
            job: Job instance from the domain layer

        Returns:
            JobListing: Converted database model instance
        """
        # Convert technologies if present
        technologies = []
        main_technologies = []

        if job.technologies:
            technologies = [
                TechnologyInfo(
                    name=tech.name,
                    category=tech.category,
                    required=tech.required,
                )
                for tech in job.technologies.technologies
            ]
            main_technologies = job.technologies.main_technologies.copy()

        # Extract details data or use defaults
        location = ""
        work_mode = ""
        employment_type = ""
        experience_level = ""
        job_function = ""
        province = ""
        city = ""
        description = ""

        if job.details:
            location = job.details.location.value
            work_mode = job.details.work_mode.value
            employment_type = job.details.employment_type.value
            experience_level = job.details.experience_level.value
            job_function = job.details.job_function.value
            province = job.details.province
            city = job.details.city
            description = job.details.description

        # Extract requirements data or use defaults
        responsibilities = []
        skill_must_have = []
        skill_nice_to_have = []
        benefits = []

        if job.requirements:
            responsibilities = job.requirements.responsibilities.copy()
            skill_must_have = job.requirements.skill_must_have.copy()
            skill_nice_to_have = job.requirements.skill_nice_to_have.copy()
            benefits = job.requirements.benefits.copy()

        # Create JobListing instance with flat structure
        job_listing = JobListing(
            signature=job.signature,
            title=job.title,
            url=job.url,
            company=job.company,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            experience_level=experience_level,
            job_function=job_function,
            province=province,
            city=city,
            description=description,
            responsibilities=responsibilities,
            skill_must_have=skill_must_have,
            skill_nice_to_have=skill_nice_to_have,
            benefits=benefits,
            technologies=technologies,
            main_technologies=main_technologies,
            # Set stage completion based on data presence
            stage_1_completed=True,  # Always true if Job exists
            stage_2_completed=job.details is not None,
            stage_3_completed=job.requirements is not None,
            stage_4_completed=job.technologies is not None,
            stage_5_completed=False,  # Supabase sync - handled separately
        )

        return job_listing

    @staticmethod
    def to_job(job_listing: JobListing) -> Job:
        """
        Convert JobListing database model to Job domain model.

        Args:
            job_listing: JobListing instance from the database layer

        Returns:
            Job: Converted domain model instance
        """
        # Convert details if present (check if any detail field has data)
        details: JobDetails | None = None
        if any(
            [
                job_listing.location,
                job_listing.work_mode,
                job_listing.employment_type,
                job_listing.experience_level,
                job_listing.job_function,
                job_listing.province,
                job_listing.city,
                job_listing.description,
            ]
        ):
            details = JobDetails.from_dict(
                {
                    "location": job_listing.location,
                    "work_mode": job_listing.work_mode,
                    "employment_type": job_listing.employment_type,
                    "experience_level": job_listing.experience_level,
                    "job_function": job_listing.job_function,
                    "province": job_listing.province,
                    "city": job_listing.city,
                    "description": job_listing.description,
                }
            )

        # Convert requirements if present (check if any requirement field has data)
        requirements: JobRequirements | None = None
        if any(
            [
                job_listing.responsibilities,
                job_listing.skill_must_have,
                job_listing.skill_nice_to_have,
                job_listing.benefits,
            ]
        ):
            requirements = JobRequirements(
                responsibilities=job_listing.responsibilities.copy(),
                skill_must_have=job_listing.skill_must_have.copy(),
                skill_nice_to_have=job_listing.skill_nice_to_have.copy(),
                benefits=job_listing.benefits.copy(),
            )

        # Convert technologies if present
        technologies: JobTechnologies | None = None
        if job_listing.technologies or job_listing.main_technologies:
            tech_list = [
                Technology(
                    name=tech.name,
                    category=tech.category,
                    required=tech.required,
                )
                for tech in job_listing.technologies
            ]

            technologies = JobTechnologies(
                technologies=tech_list,
                main_technologies=job_listing.main_technologies.copy(),
            )

        # Create Job instance
        job = Job(
            title=job_listing.title,
            url=job_listing.url,
            signature=job_listing.signature,
            company=job_listing.company,
            details=details,
            requirements=requirements,
            technologies=technologies,
        )

        return job

    @staticmethod
    def create_job_listing_from_stage1(
        signature: str,
        title: str,
        url: str,
        company: str,
    ) -> JobListing:
        """
        Create a JobListing instance from Stage 1 data only.

        This is useful when you want to store a job listing immediately after
        Stage 1 processing before the enrichment stages.

        Args:
            signature: Unique job signature
            title: Job title
            url: Job URL
            company: Company name

        Returns:
            JobListing: New JobListing instance with only Stage 1 data
        """
        return JobListing(
            signature=signature,
            title=title,
            url=url,
            company=company,
            location="",
            work_mode="",
            employment_type="",
            experience_level="",
            job_function="",
            province="",
            city="",
            description="",
            responsibilities=[],
            skill_must_have=[],
            skill_nice_to_have=[],
            benefits=[],
            technologies=[],
            main_technologies=[],
        )

    @staticmethod
    def update_job_listing_from_job(job_listing: JobListing, job: Job) -> JobListing:
        """
        Update an existing JobListing with data from a Job instance.

        This method is useful for updating database records with new processing results
        while preserving database metadata like _id, timestamps, etc.

        Args:
            job_listing: Existing JobListing instance to update
            job: Job instance with new data

        Returns:
            JobListing: Updated JobListing instance
        """
        # Update core job data
        job_listing.title = job.title
        job_listing.url = job.url
        job_listing.signature = job.signature
        job_listing.company = job.company

        # Update details if present in job
        if job.details:
            job_listing.location = job.details.location.value
            job_listing.work_mode = job.details.work_mode.value
            job_listing.employment_type = job.details.employment_type.value
            job_listing.experience_level = job.details.experience_level.value
            job_listing.job_function = job.details.job_function.value
            job_listing.province = job.details.province
            job_listing.city = job.details.city
            job_listing.description = job.details.description
            job_listing.stage_2_completed = True

        # Update requirements if present in job
        if job.requirements:
            job_listing.responsibilities = job.requirements.responsibilities.copy()
            job_listing.skill_must_have = job.requirements.skill_must_have.copy()
            job_listing.skill_nice_to_have = job.requirements.skill_nice_to_have.copy()
            job_listing.benefits = job.requirements.benefits.copy()
            job_listing.stage_3_completed = True

        # Update technologies if present in job
        if job.technologies:
            job_listing.technologies = [
                TechnologyInfo(
                    name=tech.name,
                    category=tech.category,
                    required=tech.required,
                )
                for tech in job.technologies.technologies
            ]
            job_listing.main_technologies = job.technologies.main_technologies.copy()
            job_listing.stage_4_completed = True

        # Update timestamp
        job_listing.update_timestamp()

        return job_listing


# Convenience functions for common mapping operations
def job_to_job_listing(job: Job) -> JobListing:
    """Convenience function to convert Job to JobListing."""
    return JobMapper.to_job_listing(job)


def job_listing_to_job(job_listing: JobListing) -> Job:
    """Convenience function to convert JobListing to Job."""
    return JobMapper.to_job(job_listing)
