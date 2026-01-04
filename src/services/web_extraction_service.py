"""
Web extraction service for scraping elements from web pages.

This module provides high-level functions for extracting elements from web pages
using different parsing strategies. It handles browser management, navigation,
and error handling, delegating the actual parsing to the parsers module.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from playwright.async_api import Browser, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from core.config.integrations import WebExtractionConfig
from core.models.parsers import ParserType
from services.parsers import ElementResult, ParserFactory
from utils.exceptions import WebExtractionError

logger = logging.getLogger(__name__)


class WebExtractionService:
    """
    Service for extracting elements from web pages.

    This service manages browser lifecycle and coordinates with parsers
    to extract elements from web pages with enhanced error handling and retry logic.
    """

    def __init__(self, config: WebExtractionConfig):
        """
        Initialize the extraction service.

        Args:
            config: Configuration for extraction operations
        """
        self.config = config

    @asynccontextmanager
    async def _browser_context(self):
        """Context manager for browser lifecycle."""
        browser = None
        playwright = None
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.config.browser_config.headless
            )
            yield browser
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

    @asynccontextmanager
    async def _page_context(self, browser: Browser):
        """Context manager for page lifecycle with configuration."""
        context_options: dict[str, Any] = {}

        if self.config.browser_config.viewport:
            context_options["viewport"] = self.config.browser_config.viewport
        if self.config.browser_config.user_agent:
            context_options["user_agent"] = self.config.browser_config.user_agent
        if self.config.browser_config.extra_headers:
            context_options["extra_http_headers"] = (
                self.config.browser_config.extra_headers
            )

        context = (
            await browser.new_context(**context_options) if context_options else None
        )
        page = await (context.new_page() if context else browser.new_page())

        try:
            yield page
        finally:
            await page.close()
            if context:
                await context.close()

    async def extract_elements(
        self,
        url: str,
        selectors: list[str],
        parser_type: ParserType | None = None,
        company_name: str | None = None,
    ) -> list[ElementResult]:
        """
        Extract elements from a web page using specified selectors.

        Args:
            url: The URL to extract elements from
            selectors: List of CSS selectors to extract
            parser_type: Optional parser type override (uses config default if not specified)
            company_name: Optional company name for error context

        Returns:
            List of ElementResult objects containing extraction results

        Raises:
            WebExtractionError: If extraction fails and retry is not enabled
        """
        parser_type = parser_type or self.config.parser_type
        results: list[ElementResult] = []

        try:
            async with (
                self._browser_context() as browser,
                self._page_context(browser) as page,
            ):
                try:
                    # Navigate to URL
                    await page.goto(
                        url,
                        wait_until=self.config.browser_config.wait_until,
                        timeout=self.config.browser_config.timeout,
                    )
                    logger.debug("Initial page load complete")

                except PlaywrightTimeoutError as e:
                    logger.error(f"Page load timeout for {url}")
                    raise WebExtractionError(url, e, company_name) from e

                except Exception as e:
                    logger.error(f"Failed to navigate to {url}: {e}")
                    raise WebExtractionError(url, e, company_name) from e

                # Create and run parser (only once, after navigation attempt)
                try:
                    parser = ParserFactory.create_parser(parser_type, page, selectors)
                    results = await parser.parse()
                except Exception as parse_error:
                    logger.error(f"Failed to parse content from {url}: {parse_error}")
                    raise WebExtractionError(
                        url, parse_error, company_name
                    ) from parse_error

        except WebExtractionError:
            # Re-raise WebExtractionError as-is
            raise
        except Exception as e:
            # Wrap any other unexpected errors
            logger.error(f"Unexpected error during extraction from {url}: {e}")
            raise WebExtractionError(url, e, company_name) from e

        return results

    async def extract_html_content(
        self,
        url: str,
        selectors: list[str],
        parser_type: ParserType | None = None,
        company_name: str | None = None,
    ) -> str:
        """
        Extract HTML content from specified selectors on a webpage.

        Args:
            url: The URL to extract content from
            selectors: List of CSS selectors to extract content from
            parser_type: Parser type to use for extraction
            company_name: Company name for logging context

        Returns:
            Concatenated HTML content from all selectors

        Raises:
            WebExtractionError: If extraction fails after all retries
        """
        parser_type = parser_type or self.config.parser_type

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(
                    f"Extracting HTML content from {url} (attempt {attempt + 1})"
                )

                # Use existing extract_elements method
                results = await self.extract_elements(
                    url=url,
                    selectors=selectors,
                    parser_type=parser_type,
                    company_name=company_name,
                )

                # Collect HTML content from all successful results
                html_contents = []
                successful_selectors = []

                for result in results:
                    if result.found and result.html_content:
                        html_contents.append(result.html_content)
                        successful_selectors.append(result.selector)
                        logger.info(
                            f"Extracted content from selector: {result.selector}"
                        )
                    else:
                        logger.warning(
                            f"No content found for selector: {result.selector}"
                        )

                # Check if we got any content
                if not html_contents:
                    error_msg = (
                        f"No HTML content extracted from any selectors: {selectors}"
                    )
                    logger.warning(f"{error_msg}")

                    if attempt < self.config.max_retries:
                        logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                    else:
                        raise WebExtractionError(
                            url,
                            Exception(error_msg),
                            company_name,
                            retry_attempt=attempt + 1,
                        )

                # Concatenate all HTML content with newlines
                concatenated_html = "\n".join(html_contents)

                logger.info(
                    f"Successfully extracted HTML content from "
                    f"{len(successful_selectors)} selectors: {successful_selectors}"
                )

                return concatenated_html

            except WebExtractionError:
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                error_msg = f"Unexpected error during HTML extraction: {e!s}"
                logger.error(f"{error_msg}")

                if attempt < self.config.max_retries:
                    logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                else:
                    raise WebExtractionError(
                        url, e, company_name, retry_attempt=attempt + 1
                    ) from e

        # This should never be reached, but just in case
        raise WebExtractionError(
            url,
            Exception("Maximum retries exceeded"),
            company_name,
            retry_attempt=self.config.max_retries + 1,
        )
