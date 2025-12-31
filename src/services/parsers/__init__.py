"""
Parser module for extracting content from web pages with different rendering strategies.

This module provides a flexible parser system that can handle:
- Standard HTML pages
- Greenhouse iframe-based job boards
- Angular single-page applications
- Extensible for additional parser types

Example usage:
    from parsers import ParserFactory, ParserType

    parser = ParserFactory.create_parser(
        ParserType.ANGULAR,
        page,
        selectors
    )
    results = await parser.parse()
"""

from services.parsers.base import SelectorParser
from services.parsers.factory import ParserFactory
from services.parsers.instances import (
    AngularParser,
    DefaultParser,
    DynamicJSParser,
    GreenhouseParser,
    IframeParser,
)
from services.parsers.models import ElementResult, ParseContext

__all__ = [
    "AngularParser",
    "DefaultParser",
    "DynamicJSParser",
    "ElementResult",
    "GreenhouseParser",
    "IframeParser",
    "ParseContext",
    "ParserFactory",
    "SelectorParser",
]

__version__ = "1.0.0"
