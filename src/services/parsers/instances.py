"""Concrete parser implementations for different content types."""

import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from core.models.parsers import ParserType
from services.parsers.base import SelectorParser
from services.parsers.models import ElementResult, ParseContext

logger = logging.getLogger(__name__)


class DefaultParser(SelectorParser):
    """Parser for standard HTML pages."""

    def __init__(self, page, selectors):
        super().__init__(page, selectors)
        self.parser_type = ParserType.DEFAULT

    async def setup(self) -> ParseContext:
        """Setup for default parsing - no special handling needed."""
        logger.debug("Using default parser for standard HTML")
        return ParseContext(page=self.page, parser_type=ParserType.DEFAULT)

    async def wait_for_content(self, context: ParseContext) -> None:
        """Wait for standard page load."""
        try:
            await context.page.wait_for_load_state("domcontentloaded", timeout=30000)
            logger.debug("Page reached domcontentloaded state")
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout - proceeding with available content")
            # Continue anyway - content might still be available


class GreenhouseParser(SelectorParser):
    """Parser for Greenhouse iframe-based job boards."""

    def __init__(self, page, selectors):
        super().__init__(page, selectors)
        self.parser_type = ParserType.GREENHOUSE

    async def setup(self) -> ParseContext:
        """Setup Greenhouse iframe context."""
        logger.debug("Using Greenhouse parser - looking for iframe")

        try:
            # Look for Greenhouse iframe
            greenhouse_iframe = await self.page.wait_for_selector(
                "#grnhse_iframe", timeout=5000
            )

            if greenhouse_iframe:
                frame = await greenhouse_iframe.content_frame()
                if frame:
                    logger.debug("Successfully accessed Greenhouse iframe")
                    return ParseContext(
                        page=self.page, frame=frame, parser_type=ParserType.GREENHOUSE
                    )
                else:
                    logger.warning(
                        "Could not access iframe content, falling back to main page"
                    )
        except Exception as e:
            logger.warning(f"Greenhouse iframe not found: {e}, using main page")

        return ParseContext(page=self.page, parser_type=ParserType.GREENHOUSE)

    async def wait_for_content(self, context: ParseContext) -> None:
        """Wait for iframe content to load."""
        try:
            if context.frame:
                await context.frame.wait_for_load_state(
                    "domcontentloaded", timeout=30000
                )
                logger.debug("Iframe content loaded")
            else:
                await context.page.wait_for_load_state(
                    "domcontentloaded", timeout=30000
                )
        except PlaywrightTimeoutError:
            logger.warning("Load state timeout - proceeding with available content")

    async def extract_element(
        self, context: ParseContext, selector: str, timeout: int = 5000
    ) -> ElementResult:
        """Try iframe first, then fall back to main page if needed."""
        # Try iframe first if available
        if context.frame:
            result = await super().extract_element(context, selector, timeout)
            if result.found:
                return result

            # Fallback to main page
            logger.info(f"Selector not found in iframe, trying main page: {selector}")
            main_context = ParseContext(
                page=context.page, parser_type=context.parser_type
            )
            return await super().extract_element(main_context, selector, timeout=2000)

        # No iframe, use main page
        return await super().extract_element(context, selector, timeout)


class AngularParser(SelectorParser):
    """Parser for Angular applications with dynamic content."""

    def __init__(self, page, selectors):
        super().__init__(page, selectors)
        self.parser_type = ParserType.ANGULAR

    async def setup(self) -> ParseContext:
        """Setup for Angular parsing."""
        logger.debug("Using Angular parser for dynamic content")
        return ParseContext(page=self.page, parser_type=ParserType.ANGULAR)

    async def wait_for_content(self, context: ParseContext) -> None:
        """Wait for Angular to render dynamic content."""
        try:
            # For Angular, use 'domcontentloaded' or 'commit' instead of 'networkidle'
            # as Angular apps often never reach networkidle state
            await context.page.wait_for_load_state("domcontentloaded", timeout=30000)
            logger.debug("DOM content loaded")

            # Wait a bit for initial Angular bootstrapping
            await context.page.wait_for_timeout(2000)

            # Try to wait for Angular-specific indicators with a shorter timeout
            try:
                await context.page.wait_for_function(
                    """
                    () => {
                        // Check for any Angular indicators
                        const hasAngularElements =
                            document.querySelector('[ng-version]') !== null ||
                            document.querySelector('app-root') !== null ||
                            document.querySelectorAll('[_ngcontent-ng-c]').length > 0 ||
                            document.querySelectorAll('.ng-star-inserted').length > 0;

                        // Also check if there's actual content (not just Angular shell)
                        const hasContent = document.body.innerText.trim().length > 100;

                        return hasAngularElements || hasContent;
                    }
                    """,
                    timeout=10000,
                )
                logger.debug("Angular content detected")

            except PlaywrightTimeoutError:
                logger.warning("Angular indicators not found, but proceeding anyway")

            # Give Angular components time to render
            await context.page.wait_for_timeout(3000)

        except PlaywrightTimeoutError as e:
            logger.warning(f"Angular content wait timeout: {e}")
            # Don't re-raise - continue with what we have
        except Exception as e:
            logger.error(f"Unexpected error waiting for Angular content: {e}")
            # Don't re-raise - continue with what we have

    async def extract_element(
        self,
        context: ParseContext,
        selector: str,
        timeout: int = 10000,  # Longer timeout for Angular
    ) -> ElementResult:
        """Extract element with extended timeout for Angular."""
        return await super().extract_element(context, selector, timeout)


class DynamicJSParser(SelectorParser):
    """Parser for JavaScript framework applications (React, Next.js, Vue, etc.).

    This parser is designed for modern JavaScript frameworks that render content
    dynamically after the initial page load. It waits for network activity to settle
    and allows additional time for client-side hydration and rendering.
    """

    def __init__(self, page, selectors):
        super().__init__(page, selectors)
        self.parser_type = ParserType.DYNAMIC_JS

    async def setup(self) -> ParseContext:
        """Setup for dynamic JS parsing."""
        logger.debug("Using DynamicJS parser for JavaScript framework content")
        return ParseContext(page=self.page, parser_type=ParserType.DYNAMIC_JS)

    async def wait_for_content(self, context: ParseContext) -> None:
        """Wait for JavaScript framework to render dynamic content."""
        try:
            # Trigger user interaction to bypass deferred JavaScript execution
            # Some sites (using WP Rocket, LiteSpeed Cache, etc.) delay JS until
            # user interaction (scroll, mouse move, click). This simulates that.
            await self._trigger_deferred_scripts(context)

            # Wait for initial DOM to be ready
            await context.page.wait_for_load_state("domcontentloaded", timeout=30000)
            logger.debug("DOM content loaded")

            # Wait for network idle - critical for JS frameworks that fetch data
            try:
                await context.page.wait_for_load_state("networkidle", timeout=15000)
                logger.debug("Page reached network idle state")
            except PlaywrightTimeoutError:
                logger.debug("Network idle timeout - continuing with available content")

            # Additional delay for client-side hydration and rendering
            # React, Next.js, Vue need time to hydrate and render after data fetch
            await context.page.wait_for_timeout(2000)
            logger.debug("Completed hydration wait period")

        except PlaywrightTimeoutError as e:
            logger.warning(f"DynamicJS content wait timeout: {e}")
        except Exception as e:
            logger.error(f"Unexpected error waiting for DynamicJS content: {e}")

    async def _trigger_deferred_scripts(self, context: ParseContext) -> None:
        """Simulate user interaction to trigger deferred JavaScript execution.

        Many WordPress sites use caching plugins (WP Rocket, LiteSpeed, etc.) that
        defer JavaScript execution until user interaction. This method simulates
        mouse movement and scrolling to trigger those deferred scripts.
        """
        try:
            # Simulate mouse movement
            await context.page.mouse.move(100, 100)
            await context.page.mouse.move(200, 200)

            # Simulate scroll (triggers scroll event listeners)
            await context.page.evaluate("window.scrollBy(0, 100)")
            await context.page.wait_for_timeout(300)
            await context.page.evaluate("window.scrollBy(0, -100)")

            # Dispatch mouseover event on body (some scripts listen for this)
            await context.page.evaluate(
                "document.body.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}))"
            )

            logger.debug("User interaction simulated for deferred JS trigger")
        except Exception as e:
            logger.debug(f"Could not simulate user interaction: {e}")

    async def extract_element(
        self,
        context: ParseContext,
        selector: str,
        timeout: int = 10000,  # Longer timeout for dynamic content
    ) -> ElementResult:
        """Extract element with extended timeout for dynamic JS content."""
        return await super().extract_element(context, selector, timeout)


class IframeParser(SelectorParser):
    """Parser for extracting content from within iframes.

    This parser automatically finds the first iframe on the page, accesses its
    content frame, and extracts elements from within. It's useful for pages that
    embed external content (like job boards) inside iframes.

    Usage:
        url = "https://example.com/careers"  # Parent page with iframe
        selectors = ["xpath=/html/body/div/main/ul"]  # Selectors for iframe content
        parser_type = ParserType.IFRAME
    """

    def __init__(self, page, selectors):
        super().__init__(page, selectors)
        self.parser_type = ParserType.IFRAME

    async def setup(self) -> ParseContext:
        """Setup iframe context by finding and accessing the first iframe."""
        logger.debug("Using Iframe parser - looking for first iframe on page")

        try:
            # Wait for the page to have at least one iframe
            iframe_element = await self.page.wait_for_selector("iframe", timeout=10000)

            if iframe_element:
                # Get iframe src for logging
                iframe_src = await iframe_element.get_attribute("src")
                logger.debug(f"Found iframe with src: {iframe_src}")

                frame = await iframe_element.content_frame()
                if frame:
                    logger.debug("Successfully accessed iframe content frame")
                    return ParseContext(
                        page=self.page, frame=frame, parser_type=ParserType.IFRAME
                    )
                else:
                    logger.warning(
                        "Could not access iframe content frame, falling back to main page"
                    )
        except PlaywrightTimeoutError:
            logger.warning("No iframe found on page within timeout, using main page")
        except Exception as e:
            logger.warning(f"Error accessing iframe: {e}, using main page")

        return ParseContext(page=self.page, parser_type=ParserType.IFRAME)

    async def wait_for_content(self, context: ParseContext) -> None:
        """Wait for iframe content to fully load."""
        try:
            if context.frame:
                # Wait for iframe DOM to be ready
                await context.frame.wait_for_load_state(
                    "domcontentloaded", timeout=30000
                )
                logger.debug("Iframe content loaded (domcontentloaded)")

                # Try to wait for network idle for dynamic content inside iframe
                try:
                    await context.frame.wait_for_load_state(
                        "networkidle", timeout=15000
                    )
                    logger.debug("Iframe reached network idle state")
                except PlaywrightTimeoutError:
                    logger.debug(
                        "Iframe network idle timeout - continuing with available content"
                    )

                # Additional wait for JS rendering inside iframe
                await context.frame.wait_for_timeout(1000)
                logger.debug("Completed iframe content wait period")
            else:
                await context.page.wait_for_load_state(
                    "domcontentloaded", timeout=30000
                )
        except PlaywrightTimeoutError:
            logger.warning("Iframe load timeout - proceeding with available content")
        except Exception as e:
            logger.error(f"Unexpected error waiting for iframe content: {e}")

    async def extract_element(
        self,
        context: ParseContext,
        selector: str,
        timeout: int = 10000,  # Longer timeout for iframe content
    ) -> ElementResult:
        """Extract element from iframe with fallback to main page."""
        # Try iframe first if available
        if context.frame:
            result = await super().extract_element(context, selector, timeout)
            if result.found:
                return result

            # Fallback to main page if not found in iframe
            logger.info(f"Selector not found in iframe, trying main page: {selector}")
            main_context = ParseContext(
                page=context.page, parser_type=context.parser_type
            )
            return await super().extract_element(main_context, selector, timeout=5000)

        # No iframe available, use main page
        return await super().extract_element(context, selector, timeout)
