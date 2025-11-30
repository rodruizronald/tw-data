"""
Core configuration module.

This module provides configuration classes for system paths, external service
integrations, and service-specific settings used throughout the application.
"""

from core.config.database import DatabaseConfig, SupabaseConfig
from core.config.integrations import (
    BrowserConfig,
    IntegrationsConfig,
    OpenAIConfig,
    WebExtractionConfig,
)
from core.config.services import OpenAIServiceConfig, WebParserConfig
from core.config.system import PathsConfig

__all__ = [
    "BrowserConfig",
    "DatabaseConfig",
    "IntegrationsConfig",
    "OpenAIConfig",
    "OpenAIServiceConfig",
    "PathsConfig",
    "SupabaseConfig",
    "WebExtractionConfig",
    "WebParserConfig",
]
