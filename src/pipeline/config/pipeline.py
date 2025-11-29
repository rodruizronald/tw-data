import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from core.config.integrations import (
    BrowserConfig,
    IntegrationsConfig,
    OpenAIConfig,
    WebExtractionConfig,
)
from core.config.services import OpenAIServiceConfig
from core.config.system import PathsConfig
from core.models.parsers import ParserType
from pipeline.config.stages import StageConfig, StagesConfig

# Load environment variables when this module is imported
# Try to find .env file in current directory or parent directories
current_dir = Path.cwd()
for parent in [current_dir, *list(current_dir.parents)]:
    env_path = parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        break


@dataclass
class PipelineConfig:
    """Main configuration for the job pipeline."""

    name: str
    version: str
    description: str
    enabled: bool
    paths: PathsConfig
    integrations: IntegrationsConfig
    stages: StagesConfig

    @classmethod
    def _create_stage_config(cls, stage_data: dict[str, Any]) -> StageConfig:
        """
        Create a StageConfig from stage data dictionary.

        Args:
            stage_data: Dictionary containing stage configuration data

        Returns:
            Configured StageConfig instance
        """
        openai_service_data = stage_data.get("openai_service", {})
        openai_service = OpenAIServiceConfig(**openai_service_data)

        return StageConfig(
            name=stage_data.get("name", ""),
            tag=stage_data.get("tag", ""),
            description=stage_data.get("description", ""),
            enabled=stage_data.get("enabled", True),
            openai_service=openai_service,
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "PipelineConfig":
        """Create configuration from dictionary with proper type conversion."""
        # Convert paths
        paths_data = config_dict.get("paths", {})

        paths = PathsConfig(
            prompts_dir=Path(paths_data.get("prompts_dir", "prompts")),
            companies_file=Path(paths_data.get("companies_file", "companies.yaml")),
        )

        # Convert integrations
        integrations_data = config_dict.get("integrations", {})

        # Handle OpenAI config
        openai_data = integrations_data.get("openai", {})
        openai_config = OpenAIConfig(**openai_data)

        # Handle web extraction config with nested browser config
        web_extraction_data = integrations_data.get("web_extraction", {})
        browser_config_data = web_extraction_data.get("browser_config", {})
        browser_config = BrowserConfig(**browser_config_data)

        # Convert parser_type string to enum if needed
        parser_type_value = web_extraction_data.get("parser_type", "default")
        if isinstance(parser_type_value, str):
            parser_type = ParserType(parser_type_value)
        else:
            parser_type = parser_type_value

        web_extraction_config = WebExtractionConfig(
            browser_config=browser_config,
            max_retries=web_extraction_data.get("max_retries", 3),
            retry_delay=web_extraction_data.get("retry_delay", 1.0),
            parser_type=parser_type,
        )

        integrations = IntegrationsConfig(
            openai=openai_config,
            web_extraction=web_extraction_config,
        )

        # Convert stages
        stages_data = config_dict.get("stages", {})
        stage_1_data = stages_data.get("stage_1", {})
        stage_2_data = stages_data.get("stage_2", {})
        stage_3_data = stages_data.get("stage_3", {})
        stage_4_data = stages_data.get("stage_4", {})

        # Create stage configurations using helper method
        stage_1_config = cls._create_stage_config(stage_1_data)
        stage_2_config = cls._create_stage_config(stage_2_data)
        stage_3_config = cls._create_stage_config(stage_3_data)
        stage_4_config = cls._create_stage_config(stage_4_data)

        stages = StagesConfig(
            stage_1=stage_1_config,
            stage_2=stage_2_config,
            stage_3=stage_3_config,
            stage_4=stage_4_config,
        )

        return cls(
            name=config_dict["name"],
            version=config_dict["version"],
            description=config_dict["description"],
            enabled=config_dict.get("enabled", True),
            paths=paths,
            integrations=integrations,
            stages=stages,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "paths": {
                "prompts_dir": str(self.paths.prompts_dir),
                "companies_file": str(self.paths.companies_file),
                "project_root": str(self.paths.project_root),
            },
            "integrations": {
                "openai": {
                    "model": self.openai.model,
                    "max_retries": self.openai.max_retries,
                    "timeout": self.openai.timeout,
                    "api_key": self.openai.api_key,
                },
                "web_extraction": {
                    "browser_config": {
                        "headless": self.web_extraction.browser_config.headless,
                        "viewport": self.web_extraction.browser_config.viewport,
                        "user_agent": self.web_extraction.browser_config.user_agent,
                        "timeout": self.web_extraction.browser_config.timeout,
                        "wait_until": self.web_extraction.browser_config.wait_until,
                        "extra_headers": self.web_extraction.browser_config.extra_headers,
                    },
                    "parser_type": self.web_extraction.parser_type.value,
                    "max_retries": self.web_extraction.max_retries,
                    "retry_delay": self.web_extraction.retry_delay,
                },
            },
            "stages": {
                "stage_1": {
                    "name": self.stage_1.name,
                    "tag": self.stage_1.tag,
                    "description": self.stage_1.description,
                    "enabled": self.stage_1.enabled,
                    "openai_service": {
                        "system_message": self.stage_1.openai_service.system_message,
                        "prompt_template": self.stage_1.openai_service.prompt_template,
                        "prompt_variables": self.stage_1.openai_service.prompt_variables,
                        "response_format": self.stage_1.openai_service.response_format,
                    },
                },
                "stage_2": {
                    "name": self.stage_2.name,
                    "tag": self.stage_2.tag,
                    "description": self.stage_2.description,
                    "enabled": self.stage_2.enabled,
                    "openai_service": {
                        "system_message": self.stage_2.openai_service.system_message,
                        "prompt_template": self.stage_2.openai_service.prompt_template,
                        "prompt_variables": self.stage_2.openai_service.prompt_variables,
                        "response_format": self.stage_2.openai_service.response_format,
                    },
                },
                "stage_3": {
                    "name": self.stage_3.name,
                    "tag": self.stage_3.tag,
                    "description": self.stage_3.description,
                    "enabled": self.stage_3.enabled,
                    "openai_service": {
                        "system_message": self.stage_3.openai_service.system_message,
                        "prompt_template": self.stage_3.openai_service.prompt_template,
                        "prompt_variables": self.stage_3.openai_service.prompt_variables,
                        "response_format": self.stage_3.openai_service.response_format,
                    },
                },
                "stage_4": {
                    "name": self.stage_4.name,
                    "tag": self.stage_4.tag,
                    "description": self.stage_4.description,
                    "enabled": self.stage_4.enabled,
                    "openai_service": {
                        "system_message": self.stage_4.openai_service.system_message,
                        "prompt_template": self.stage_4.openai_service.prompt_template,
                        "prompt_variables": self.stage_4.openai_service.prompt_variables,
                        "response_format": self.stage_4.openai_service.response_format,
                    },
                },
            },
        }

    @classmethod
    def load(cls) -> "PipelineConfig":
        """
        Load configuration from environment variables and YAML file.

        Args:
            env_file: Optional path to .env file

        Returns:
            Configured PipelineConfig instance
        """
        # Use current working directory as project root (works in Docker)
        project_root = Path.cwd()

        # Load pipeline.yaml configuration
        pipeline_config_file = os.getenv("PIPELINE_CONFIG_FILE", "pipeline.yaml")
        pipeline_config_path = project_root / pipeline_config_file

        if not pipeline_config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {pipeline_config_path}"
            )

        with open(pipeline_config_path, encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
            pipeline_dict = full_config.get("pipeline", {})
            config = cls.from_dict(pipeline_dict)

        config.paths.project_root = project_root
        return config

    def get_prompt_path(self, prompt_filename: str) -> Path:
        """
        Get the full path to a prompt template file.

        Args:
            prompt_filename: Name of the prompt file (e.g., "job_extraction.md")

        Returns:
            Full path to the prompt template file
        """
        prompts_dir: Path = self.paths.prompts_dir
        return prompts_dir / prompt_filename

    def initialize_paths(self) -> None:
        """Initialize all paths using the project root and stages configuration."""
        # Initialize paths with stages configuration
        self.paths.initialize_paths()

    @property
    def companies_file_path(self) -> Path:
        """Get the full path to the companies file."""
        companies_file: Path = self.paths.companies_file
        return companies_file

    @property
    def openai(self) -> OpenAIConfig:
        """Get OpenAI configuration."""
        return self.integrations.openai

    @property
    def web_extraction(self) -> WebExtractionConfig:
        """Get web extraction configuration."""
        return self.integrations.web_extraction

    @property
    def stage_1(self) -> StageConfig:
        """Get Stage 1 configuration."""
        return self.stages.stage_1

    @property
    def stage_2(self) -> StageConfig:
        """Get Stage 2 configuration."""
        return self.stages.stage_2

    @property
    def stage_3(self) -> StageConfig:
        """Get Stage 3 configuration."""
        return self.stages.stage_3

    @property
    def stage_4(self) -> StageConfig:
        """Get Stage 4 configuration."""
        return self.stages.stage_4
