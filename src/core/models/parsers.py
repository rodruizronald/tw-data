"""Parser-related models."""

from enum import Enum


class ParserType(str, Enum):
    """Types of parsers available for job extraction."""

    DEFAULT = "default"
    GREENHOUSE = "greenhouse"
    ANGULAR = "angular"
    DYNAMIC_JS = "dynamic_js"
    IFRAME = "iframe"
