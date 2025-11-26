import hashlib
import logging
from typing import Any

from core.models.jobs import (
    EmploymentType,
    ExperienceLevel,
    Job,
    JobDetails,
    JobFunction,
    JobRequirements,
    JobTechnologies,
    Location,
    Technology,
    WorkMode,
)

logger = logging.getLogger(__name__)


class JobMapper:
    """Maps dictionary containing job data to Job model."""

    def map_from_openai_response(
        self, response: dict[str, Any], company: str
    ) -> list[Job]:
        """
        Map dictionary containing multiple jobs to list of Job models.

        Args:
            response: Dictionary containing jobs data
            company: Company name to associate with the jobs

        Returns:
            List of validated Job objects

        Raises:
            ValueError: If response format is invalid or required fields are missing
        """
        try:
            jobs = []
            job_data = response.get("jobs", [])

            if not isinstance(job_data, list):
                raise ValueError(f"Invalid jobs data format: {job_data}")

            for i, job_info in enumerate(job_data):
                try:
                    if not isinstance(job_info, dict):
                        logger.warning(
                            f"Skipping invalid job item at index {i}: not a dictionary"
                        )
                        continue

                    # Map and validate each field
                    title = self._extract_title(job_info)
                    url = self._extract_url(job_info)

                    # Generate a unique signature for a job URL.
                    signature = hashlib.sha256(url.encode()).hexdigest()

                    job = Job(
                        title=title,
                        url=url,
                        signature=signature,
                        company=company,
                    )
                    jobs.append(job)

                except Exception as e:
                    logger.warning(f"Skipping invalid job data at index {i}: {e}")
                    continue

            return jobs

        except Exception as e:
            logger.error(f"Failed to map response to Job: {e}")
            raise ValueError(f"Invalid response format: {e}") from e

    def _extract_title(self, job_data: dict[str, Any]) -> str:
        """Extract and validate title field."""
        title = job_data.get("title")
        if not title:
            raise ValueError("Missing title field")

        if not isinstance(title, str):
            raise ValueError(f"Invalid title value: {title}")

        title_str = title.strip()
        if not title_str:
            raise ValueError("Title cannot be empty")

        return title_str

    def _extract_url(self, job_data: dict[str, Any]) -> str:
        """Extract and validate URL field."""
        url = job_data.get("url")
        if not url:
            raise ValueError("Missing url field")

        if not isinstance(url, str):
            raise ValueError(f"Invalid url value: {url}")

        url_str = url.strip()
        if not url_str:
            raise ValueError("URL cannot be empty")

        # Basic URL validation
        if not (url_str.startswith("http://") or url_str.startswith("https://")):
            raise ValueError(f"Invalid URL format: {url_str}")

        return url_str


class JobDetailsMapper:
    """Maps dictionary containing job details data to JobDetails model."""

    def map_from_openai_response(self, response: dict[str, Any]) -> JobDetails:
        """
        Map dictionary to JobDetails model.

        Args:
            response: Dictionary containing job details data

        Returns:
            JobDetails: Validated and typed job details

        Raises:
            ValueError: If response format is invalid or required fields are missing
        """
        try:
            # Map and validate each field
            location = self._extract_location(response)
            work_mode = self._extract_work_mode(response)
            employment_type = self._extract_employment_type(response)
            experience_level = self._extract_experience_level(response)
            job_function = self._extract_job_function(response)
            province = self._extract_province(response)
            city = self._extract_city(response)
            description = self._extract_description(response)

            return JobDetails(
                location=location,
                work_mode=work_mode,
                employment_type=employment_type,
                experience_level=experience_level,
                job_function=job_function,
                province=province,
                city=city,
                description=description,
            )

        except Exception as e:
            logger.error(f"Failed to map OpenAI response to JobDetails: {e}")
            raise ValueError(f"Invalid OpenAI response format: {e}") from e

    def _extract_location(self, job_data: dict[str, Any]) -> Location:
        """Extract and validate location field."""
        location_str = job_data.get("location")
        if not location_str:
            raise ValueError("Missing location field")

        try:
            return Location(location_str)
        except ValueError as err:
            raise ValueError(f"Invalid location value: {location_str}") from err

    def _extract_work_mode(self, job_data: dict[str, Any]) -> WorkMode:
        """Extract and validate work_mode field."""
        work_mode_str = job_data.get("work_mode")
        if not work_mode_str:
            raise ValueError("Missing work_mode field")

        try:
            return WorkMode(work_mode_str)
        except ValueError as err:
            raise ValueError(f"Invalid work_mode value: {work_mode_str}") from err

    def _extract_employment_type(self, job_data: dict[str, Any]) -> EmploymentType:
        """Extract and validate employment_type field."""
        employment_type_str = job_data.get("employment_type")
        if not employment_type_str:
            raise ValueError("Missing employment_type field")

        try:
            return EmploymentType(employment_type_str)
        except ValueError as err:
            raise ValueError(
                f"Invalid employment_type value: {employment_type_str}"
            ) from err

    def _extract_experience_level(self, job_data: dict[str, Any]) -> ExperienceLevel:
        """Extract and validate experience_level field."""
        experience_level_str = job_data.get("experience_level")
        if not experience_level_str:
            raise ValueError("Missing experience_level field")

        try:
            return ExperienceLevel(experience_level_str)
        except ValueError as err:
            raise ValueError(
                f"Invalid experience_level value: {experience_level_str}"
            ) from err

    def _extract_job_function(self, job_data: dict[str, Any]) -> JobFunction:
        """Extract and validate job_function field."""
        job_function_str = job_data.get("job_function")
        if not job_function_str:
            raise ValueError("Missing job_function field")

        try:
            return JobFunction(job_function_str)
        except ValueError as err:
            raise ValueError(f"Invalid job_function value: {job_function_str}") from err

    def _extract_province(self, job_data: dict[str, Any]) -> str:
        """Extract and validate province field."""
        province = job_data.get("province", "")

        if not isinstance(province, str):
            raise ValueError(f"Invalid province value: {province}")

        return province.strip()

    def _extract_city(self, job_data: dict[str, Any]) -> str:
        """Extract and validate city field."""
        city = job_data.get("city", "")

        if not isinstance(city, str):
            raise ValueError(f"Invalid city value: {city}")

        return city.strip()

    def _extract_description(self, job_data: dict[str, Any]) -> str:
        """Extract and validate description field."""
        description = job_data.get("description")
        if not isinstance(description, str) or not description:
            raise ValueError(f"Invalid description value: {description}")

        # Validate max length as per prompt requirements
        if len(description) > 500:
            logger.warning(f"Description exceeds 500 characters: {len(description)}")

        return description.strip()


class JobRequirementsMapper:
    """Maps dictionary containing job requirements data to JobRequirements model."""

    def map_from_openai_response(self, response: dict[str, Any]) -> JobRequirements:
        """
        Map dictionary to JobRequirements model.

        Args:
            response: Dictionary containing job requirements data

        Returns:
            JobRequirements: Validated and typed job requirements

        Raises:
            ValueError: If response format is invalid or required fields are missing
        """
        try:
            # Map and validate each field
            responsibilities = self._extract_responsibilities(response)
            skill_must_have = self._extract_skill_must_have(response)
            skill_nice_to_have = self._extract_skill_nice_to_have(response)
            benefits = self._extract_benefits(response)

            return JobRequirements(
                responsibilities=responsibilities,
                skill_must_have=skill_must_have,
                skill_nice_to_have=skill_nice_to_have,
                benefits=benefits,
            )

        except Exception as e:
            logger.error(f"Failed to map OpenAI response to JobRequirements: {e}")
            raise ValueError(f"Invalid OpenAI response format: {e}") from e

    def _extract_responsibilities(self, job_data: dict[str, Any]) -> list[str]:
        """Extract and validate responsibilities field."""
        responsibilities = job_data.get("responsibilities")
        if not isinstance(responsibilities, list):
            raise ValueError(f"Invalid responsibilities value: {responsibilities}")

        # Validate each item is a string
        for i, item in enumerate(responsibilities):
            if not isinstance(item, str):
                raise ValueError(f"Invalid responsibility item at index {i}: {item}")

        return [item.strip() for item in responsibilities if item.strip()]

    def _extract_skill_must_have(self, job_data: dict[str, Any]) -> list[str]:
        """Extract and validate skill_must_have field."""
        skill_must_have = job_data.get("skill_must_have")
        if not isinstance(skill_must_have, list):
            raise ValueError(f"Invalid skill_must_have value: {skill_must_have}")

        # Validate each item is a string
        for i, item in enumerate(skill_must_have):
            if not isinstance(item, str):
                raise ValueError(f"Invalid must-have skill item at index {i}: {item}")

        return [item.strip() for item in skill_must_have if item.strip()]

    def _extract_skill_nice_to_have(self, job_data: dict[str, Any]) -> list[str]:
        """Extract and validate skill_nice_to_have field."""
        skill_nice_to_have = job_data.get("skill_nice_to_have")
        if not isinstance(skill_nice_to_have, list):
            raise ValueError(f"Invalid skill_nice_to_have value: {skill_nice_to_have}")

        # Validate each item is a string
        for i, item in enumerate(skill_nice_to_have):
            if not isinstance(item, str):
                raise ValueError(
                    f"Invalid nice-to-have skill item at index {i}: {item}"
                )

        return [item.strip() for item in skill_nice_to_have if item.strip()]

    def _extract_benefits(self, job_data: dict[str, Any]) -> list[str]:
        """Extract and validate benefits field."""
        benefits = job_data.get("benefits")
        if not isinstance(benefits, list):
            raise ValueError(f"Invalid benefits value: {benefits}")

        # Validate each item is a string
        for i, item in enumerate(benefits):
            if not isinstance(item, str):
                raise ValueError(f"Invalid benefit item at index {i}: {item}")

        return [item.strip() for item in benefits if item.strip()]


class JobTechnologiesMapper:
    """Maps OpenAI response to JobTechnologies model."""

    def map_from_openai_response(self, response: dict[str, Any]) -> JobTechnologies:
        """
        Transform OpenAI response to JobTechnologies model.

        Args:
            response: Raw OpenAI response dictionary

        Returns:
            JobTechnologies: Validated and typed job technologies

        Raises:
            ValueError: If response format is invalid or required fields are missing
        """
        try:
            # Map and validate each field
            technologies = self._extract_technologies(response)
            main_technologies = self._extract_main_technologies(response)

            return JobTechnologies(
                technologies=technologies,
                main_technologies=main_technologies,
            )

        except Exception as e:
            logger.error(f"Failed to map response to JobTechnologies: {e}")
            raise ValueError(f"Invalid response format: {e}") from e

    def _extract_technologies(self, job_data: dict[str, Any]) -> list[Technology]:
        """Extract and validate technologies field."""
        technologies_data = job_data.get("technologies")
        if not isinstance(technologies_data, list):
            raise ValueError(f"Invalid technologies value: {technologies_data}")

        technologies = []
        for i, tech_data in enumerate(technologies_data):
            if not isinstance(tech_data, dict):
                raise ValueError(f"Invalid technology item at index {i}: {tech_data}")

            # Validate required fields
            name = tech_data.get("name")
            required = tech_data.get("required")

            if not name or not isinstance(name, str):
                raise ValueError(f"Invalid technology name at index {i}: {name}")
            if not isinstance(required, bool):
                raise ValueError(
                    f"Invalid technology required field at index {i}: {required}"
                )

            technologies.append(
                Technology(
                    name=name.strip(),
                    required=required,
                )
            )

        return technologies

    def _extract_main_technologies(self, job_data: dict[str, Any]) -> list[str]:
        """Extract and validate main_technologies field."""
        main_technologies = job_data.get("main_technologies")
        if not isinstance(main_technologies, list):
            raise ValueError(f"Invalid main_technologies value: {main_technologies}")

        # Validate each item is a string
        for i, tech in enumerate(main_technologies):
            if not isinstance(tech, str):
                raise ValueError(f"Invalid main technology item at index {i}: {tech}")

        return [tech.strip() for tech in main_technologies if tech.strip()]
