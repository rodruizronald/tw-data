from dataclasses import dataclass
from typing import Any

from core.models.parsers import ParserType


@dataclass
class SelectorConfig:
    """Configuration for a selector group with its parser type."""

    type: str
    values: list[str]

    def __post_init__(self):
        """Validate selector configuration."""
        # Validate parser type
        if not isinstance(self.type, str):
            raise ValueError("Selector type must be a string")
        try:
            ParserType[self.type.upper()]
        except KeyError as e:
            raise ValueError(f"Invalid parser type: {self.type}") from e

        # Validate selectors list
        if not isinstance(self.values, list):
            raise ValueError("Selector values must be a list")
        if not self.values:
            raise ValueError("Selector values cannot be empty")

    @property
    def parser_type(self) -> ParserType:
        """Get parser type as enum."""
        return ParserType[self.type.upper()]


@dataclass
class WebParserConfig:
    """Web parser configuration with per-selector parser types."""

    selectors: dict[str, SelectorConfig]

    def __post_init__(self):
        """Validate parser configuration."""
        # Validate required selector groups exist
        if "job_board" not in self.selectors:
            raise ValueError("job_board selector configuration is required")
        if "job_card" not in self.selectors:
            raise ValueError("job_card selector configuration is required")

        # Convert dict entries to SelectorConfig if needed
        for key, value in self.selectors.items():
            if isinstance(value, dict):
                self.selectors[key] = SelectorConfig(
                    type=value.get("type", ""),
                    values=value.get("values", []),
                )
            elif not isinstance(value, SelectorConfig):
                raise ValueError(
                    f"Invalid selector configuration for {key}: must be dict or SelectorConfig"
                )

    @property
    def job_board_config(self) -> SelectorConfig:
        """Get job board selector configuration."""
        return self.selectors["job_board"]

    @property
    def job_card_config(self) -> SelectorConfig:
        """Get job card selector configuration."""
        return self.selectors["job_card"]

    @property
    def job_board_selectors(self) -> list[str]:
        """Get job board selector values."""
        return self.selectors["job_board"].values

    @property
    def job_card_selectors(self) -> list[str]:
        """Get job card selector values."""
        return self.selectors["job_card"].values

    @property
    def job_board_parser_type(self) -> ParserType:
        """Get job board parser type."""
        return self.selectors["job_board"].parser_type

    @property
    def job_card_parser_type(self) -> ParserType:
        """Get job card parser type."""
        return self.selectors["job_card"].parser_type


@dataclass
class OpenAIServiceConfig:
    """Configuration for OpenAI service."""

    system_message: str
    prompt_template: str
    prompt_variables: list[str]
    response_format: dict[str, Any]

    def __post_init__(self):
        """Validate OpenAI service configuration."""
        if not self.system_message or not self.system_message.strip():
            raise ValueError("system_message cannot be empty")

        if not self.prompt_template or not self.prompt_template.strip():
            raise ValueError("prompt_template cannot be empty")

        if not isinstance(self.prompt_variables, list):
            raise ValueError("prompt_variables must be a list")

        if not self.prompt_variables:
            raise ValueError("prompt_variables cannot be empty")

        if not isinstance(self.response_format, dict):
            raise ValueError("response_format must be a dictionary")

        if not self.response_format:
            raise ValueError("response_format cannot be empty")
