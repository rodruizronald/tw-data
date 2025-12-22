from dataclasses import dataclass
from typing import Any

from core.config.services import OpenAIServiceConfig


@dataclass
class StageConfig:
    """Configuration for Stage processing."""

    name: str
    tag: str
    description: str
    enabled: bool
    openai_service: OpenAIServiceConfig

    @property
    def system_message(self) -> str:
        """Get OpenAI service system message."""
        message: str = self.openai_service.system_message
        return message

    @property
    def prompt_template(self) -> str:
        """Get OpenAI service prompt template."""
        template: str = self.openai_service.prompt_template
        return template

    @property
    def prompt_variables(self) -> list[str]:
        """Get OpenAI service prompt variables."""
        variables: list[str] = self.openai_service.prompt_variables
        return variables

    @property
    def response_format(self) -> dict[str, Any]:
        """Get OpenAI service response format."""
        format_dict: dict[str, Any] = self.openai_service.response_format
        return format_dict


@dataclass
class Stage5Config:
    """Configuration for Stage 5 processing (Supabase upload)."""

    name: str
    tag: str
    description: str
    enabled: bool


@dataclass
class StagesConfig:
    """Configuration for all stages."""

    stage_1: StageConfig
    stage_2: StageConfig
    stage_3: StageConfig
    stage_4: StageConfig
    stage_5: Stage5Config

    def get_enabled_stage_tags(self) -> list[str]:
        """
        Get a list of all enabled stages from the configuration.

        Returns:
            List of enabled stage tags (e.g., ["stage_1", "stage_2"])
        """
        enabled_stages = []

        if self.stage_1.enabled:
            enabled_stages.append(self.stage_1.tag)

        if self.stage_2.enabled:
            enabled_stages.append(self.stage_2.tag)

        if self.stage_3.enabled:
            enabled_stages.append(self.stage_3.tag)

        if self.stage_4.enabled:
            enabled_stages.append(self.stage_4.tag)

        if self.stage_5.enabled:
            enabled_stages.append(self.stage_5.tag)

        return enabled_stages
