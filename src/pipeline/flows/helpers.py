import json
from pathlib import Path

import yaml

from core.models.jobs import CompanyData, TechData
from pipeline.config import PipelineConfig


def load_companies_from_file(companies_file: Path, logger) -> list[CompanyData]:
    """
    Load companies from YAML file.

    Args:
        companies_file: Path to companies YAML file

    Returns:
        List of CompanyData objects

    Raises:
        FileNotFoundError: If companies file doesn't exist
        ValueError: If companies file format is invalid
    """
    if not companies_file.exists():
        raise FileNotFoundError(f"Companies file not found: {companies_file}")

    try:
        with open(companies_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        companies_data = data.get("companies", [])
        companies = []

        for company_dict in companies_data:
            try:
                company = CompanyData(**company_dict)
                companies.append(company)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid company data: {company_dict.get('name', 'unknown')} - {e}"
                )

        return companies

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in companies file: {e}") from e
    except Exception as e:
        raise ValueError(f"Error loading companies file: {e}") from e


def load_technologies_from_file(technologies_file: Path, logger) -> list[TechData]:
    """
    Load technologies from JSON file.

    Args:
        technologies_file: Path to technologies JSON file
        logger: Logger instance for warnings

    Returns:
        List of TechData objects

    Raises:
        FileNotFoundError: If technologies file doesn't exist
        ValueError: If technologies file format is invalid
    """
    if not technologies_file.exists():
        raise FileNotFoundError(f"Technologies file not found: {technologies_file}")

    try:
        with open(technologies_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Technologies file must contain a JSON array")

        technologies = []

        for tech_dict in data:
            try:
                tech = TechData.from_dict(tech_dict)
                technologies.append(tech)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid technology data: {tech_dict.get('name', 'unknown')} - {e}"
                )

        return technologies

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in technologies file: {e}") from e
    except Exception as e:
        raise ValueError(f"Error loading technologies file: {e}") from e


def validate_flow_inputs(
    companies: list[CompanyData],
    config: PipelineConfig,
) -> None:
    """
    Validate inputs before starting flow execution.

    Args:
        companies: List of companies to validate
        config: Pipeline configuration to validate
        prompt_template_path: Prompt template path to validate

    Raises:
        ValueError: If any input is invalid
    """
    # Validate companies
    if not companies:
        raise ValueError("No companies provided")

    enabled_count = len([c for c in companies if c.enabled])
    if enabled_count == 0:
        raise ValueError("No enabled companies found")

    # Validate prompt template
    prompt_path = config.get_prompt_path(config.stage_1.prompt_template)
    if not prompt_path.exists():
        raise ValueError(
            f"Prompt template file not found: {config.stage_1.prompt_template}"
        )

    if not prompt_path.is_file():
        raise ValueError(
            f"Prompt template path is not a file: {config.stage_1.prompt_template}"
        )
