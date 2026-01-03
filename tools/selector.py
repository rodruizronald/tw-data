"""
CSS Selector Testing Tool

A development utility for testing and validating CSS selectors on web pages
with different parsing strategies (default, greenhouse, angular, dynamic_js, iframe).

Usage:
    python -m tools.selector [--url URL] [--selectors SELECTOR1 SELECTOR2] [--parser TYPE]

    or

    python tools/selector.py

Examples:
    # Test with default configuration
    python -m tools.selector

    # Test specific URL with selectors and single parser
    python -m tools.selector --url "https://example.com" --selectors "h1" ".content" --parser default

    # Test with per-selector-group parser types
    python -m tools.selector --url "https://example.com" \\
        --job-board-selectors "xpath=//ul" --job-board-parser greenhouse \\
        --job-card-selectors "xpath=//div" --job-card-parser default

    # Load configuration from JSON file
    python -m tools.selector --config test_config.json
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from src.core.config import BrowserConfig, WebExtractionConfig
from src.core.models.parsers import ParserType
from src.services.parsers import ElementResult
from src.services.web_extraction_service import (
    WebExtractionService,
)

logger = logging.getLogger(__name__)


class SelectorTester:
    """Main class for selector testing functionality."""

    # ANSI color codes for terminal output
    COLORS: ClassVar[dict[str, str]] = {
        "GREEN": "\033[92m",
        "RED": "\033[91m",
        "YELLOW": "\033[93m",
        "BLUE": "\033[94m",
        "CYAN": "\033[96m",
        "RESET": "\033[0m",
        "BOLD": "\033[1m",
    }

    def __init__(
        self,
        save_results: bool = False,
        output_format: str = "console",
        headless: bool = True,
        browser_config: BrowserConfig | None = None,
    ):
        """
        Initialize the selector tester.

        Args:
            save_results: Whether to save results to file
            output_format: Output format ('console', 'json', 'markdown')
            headless: Whether to run browser in headless mode
            browser_config: Optional browser configuration override
        """
        self.save_results = save_results
        self.output_format = output_format
        self.results_dir = Path(__file__).parent / "results"

        # Create browser and extraction configs
        self.browser_config = browser_config or BrowserConfig(
            headless=headless, timeout=30000, wait_until="domcontentloaded"
        )

        if save_results:
            self.results_dir.mkdir(exist_ok=True)

    def _colorize(self, text: str, color: str) -> str:
        """Add color to text for terminal output."""
        if self.output_format != "console":
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['RESET']}"

    def format_result_console(self, result: ElementResult) -> str:
        """Format a single result for console output."""
        output = []
        output.append(f"{self._colorize('SELECTOR:', 'CYAN')} {result.selector}")
        output.append("-" * 60)

        if result.found:
            output.append(
                f"{self._colorize('✅ FOUND ELEMENT', 'GREEN')} in {result.context}"
            )

            if result.text_content:
                text_preview = result.text_content[:500]
                if len(result.text_content) > 500:
                    text_preview += "..."
                output.append(
                    f"\n{self._colorize('📝 TEXT CONTENT', 'BLUE')} ({len(result.text_content)} chars):"
                )
                output.append(text_preview)

            if result.html_content:
                html_preview = result.html_content[:300]
                if len(result.html_content) > 300:
                    html_preview += "..."
                output.append(
                    f"\n{self._colorize('🏷️  HTML CONTENT', 'BLUE')} ({len(result.html_content)} chars):"
                )
                output.append(html_preview)
        else:
            output.append(f"{self._colorize('❌ ELEMENT NOT FOUND', 'RED')}")
            output.append(f"Error: {result.error_message}")

        return "\n".join(output)

    def format_result_json(self, results: list[ElementResult]) -> str:
        """Format results as JSON."""
        data = []
        for result in results:
            data.append(
                {
                    "selector": result.selector,
                    "found": result.found,
                    "context": result.context,
                    "text_content": result.text_content,
                    "html_content": result.html_content,
                    "error_message": result.error_message,
                }
            )
        return json.dumps(data, indent=2)

    def format_result_markdown(self, url: str, results: list[ElementResult]) -> str:
        """Format results as Markdown."""
        output = ["# Selector Test Results\n"]
        output.append(f"**URL:** `{url}`\n")
        output.append(f"**Timestamp:** {datetime.now(UTC).astimezone().isoformat()}\n")
        output.append(f"**Total Selectors:** {len(results)}\n")
        output.append(
            f"**Found:** {sum(1 for r in results if r.found)}/{len(results)}\n"
        )
        output.append("\n## Results\n")

        for i, result in enumerate(results, 1):
            output.append(f"### {i}. Selector: `{result.selector}`\n")
            if result.found:
                output.append("- **Status:** ✅ Found\n")
                output.append(f"- **Context:** {result.context}\n")
                if result.text_content:
                    text_preview = result.text_content[:200]
                    if len(result.text_content) > 200:
                        text_preview += "..."
                    output.append(f"- **Text Content:** {text_preview}\n")
            else:
                output.append("- **Status:** ❌ Not Found\n")
                output.append(f"- **Error:** {result.error_message}\n")
            output.append("")

        return "\n".join(output)

    def _create_extraction_service(
        self, parser_type: ParserType
    ) -> WebExtractionService:
        """Create extraction service with specified parser type."""
        config = WebExtractionConfig(
            browser_config=self.browser_config,
            parser_type=parser_type,
            max_retries=2,
            retry_delay=1.0,
        )
        return WebExtractionService(config)

    async def test_selectors(
        self,
        url: str,
        selectors: list[str],
        parser_type: ParserType = ParserType.DEFAULT,
    ) -> list[ElementResult]:
        """
        Test HTML selectors on a webpage.

        Args:
            url: The URL to test
            selectors: List of CSS selectors
            parser_type: Parser type to use

        Returns:
            List of ElementResult objects
        """
        # Print header for console output
        if self.output_format == "console":
            print(f"\n{'=' * 80}")
            print(f"{self._colorize('TESTING SELECTORS ON:', 'BOLD')} {url}")
            print(f"{self._colorize('📋 PARSER:', 'CYAN')} {parser_type.value}")
            print(f"{self._colorize('📊 SELECTORS TO TEST:', 'CYAN')} {len(selectors)}")
            print(f"{'=' * 80}\n")

        # Create extraction service with specified parser type
        service = self._create_extraction_service(parser_type)

        try:
            # Extract elements using the service
            results = await service.extract_elements(
                url=url, selectors=selectors, parser_type=parser_type
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Create error results for all selectors
            results = [
                ElementResult(
                    selector=selector,
                    found=False,
                    error_message=f"Service error: {e!s}",
                    context="error",
                )
                for selector in selectors
            ]

        # Format and display results
        if self.output_format == "console":
            for i, result in enumerate(results, 1):
                print(
                    f"\n{self._colorize(f'[{i}/{len(results)}]', 'YELLOW')} {self.format_result_console(result)}"
                )
                print(f"\n{'=' * 80}")

            # Print summary
            successful = sum(1 for r in results if r.found)
            print(
                f"\n{self._colorize('📊 SUMMARY:', 'BOLD')} {successful}/{len(results)} selectors found successfully"
            )

        elif self.output_format == "json":
            print(self.format_result_json(results))

        elif self.output_format == "markdown":
            print(self.format_result_markdown(url, results))

        # Save results if requested
        if self.save_results:
            self._save_results(url, results)

        return results

    def _save_results(self, url: str, results: list[ElementResult]):
        """Save results to file."""
        timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d_%H%M%S")
        domain = url.split("/")[2].replace(".", "_")

        if self.output_format == "json":
            filename = f"{domain}_{timestamp}.json"
            filepath = self.results_dir / filename
            filepath.write_text(self.format_result_json(results))
        else:
            filename = f"{domain}_{timestamp}.md"
            filepath = self.results_dir / filename
            filepath.write_text(self.format_result_markdown(url, results))

        logger.info(f"Results saved to: {filepath}")


def load_test_config(config_file: str) -> dict[str, Any] | None:
    """Load test configuration from JSON file."""
    config_path = Path(config_file)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_file}")
        return None

    try:
        with open(config_path) as f:
            config: dict[str, Any] = json.load(f)
            return config
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading config file: {e}")
        return None


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser_choices = ["default", "greenhouse", "angular", "dynamic_js", "iframe"]

    parser = argparse.ArgumentParser(
        description="Test CSS selectors on web pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple mode with single parser for all selectors
  %(prog)s --url "https://example.com" --selectors "h1" ".content" --parser default

  # Per-selector-group mode with different parsers
  %(prog)s --url "https://example.com" \\
      --job-board-selectors "xpath=//ul" --job-board-parser greenhouse \\
      --job-card-selectors "xpath=//div" --job-card-parser default

  # Load from config file
  %(prog)s --config test_config.json
        """,
    )

    parser.add_argument("--url", type=str, help="URL to test selectors on")

    # Simple mode arguments
    parser.add_argument(
        "--selectors",
        nargs="+",
        help="CSS selectors to test (simple mode with single parser)",
    )

    parser.add_argument(
        "--parser",
        type=str,
        choices=parser_choices,
        default="default",
        help="Parser type for simple mode (default: default)",
    )

    # Per-selector-group mode arguments
    parser.add_argument(
        "--job-board-selectors",
        nargs="+",
        help="Job board selectors to test",
    )

    parser.add_argument(
        "--job-board-parser",
        type=str,
        choices=parser_choices,
        help="Parser type for job board selectors",
    )

    parser.add_argument(
        "--job-card-selectors",
        nargs="+",
        help="Job card selectors to test",
    )

    parser.add_argument(
        "--job-card-parser",
        type=str,
        choices=parser_choices,
        help="Parser type for job card selectors",
    )

    parser.add_argument(
        "--config", type=str, help="Load test configuration from JSON file"
    )

    parser.add_argument("--save", action="store_true", help="Save results to file")

    parser.add_argument(
        "--format",
        type=str,
        choices=["console", "json", "markdown"],
        default="console",
        help="Output format (default: console)",
    )

    return parser


async def _run_from_config(
    tester: SelectorTester, config: dict[str, Any]
) -> list[ElementResult]:
    """Run tests based on configuration file."""
    all_results: list[ElementResult] = []
    url: str = config.get("url", "")
    if not url:
        logger.error("URL is required in config file")
        return all_results

    selectors_config = config.get("selectors", {})

    # Check if using new per-selector-group format
    if isinstance(selectors_config, dict) and (
        "job_board" in selectors_config or "job_card" in selectors_config
    ):
        job_card_url: str = config.get("job_card_url", url)
        all_results = await _run_per_selector_group_from_config(
            tester, url, selectors_config, job_card_url
        )
    else:
        # Simple format (list of selectors)
        selectors = (
            selectors_config
            if isinstance(selectors_config, list)
            else config.get("selectors", [])
        )
        parser_type = ParserType[config.get("parser", "DEFAULT").upper()]
        all_results = await tester.test_selectors(url, selectors, parser_type)

    return all_results


async def _run_per_selector_group_from_config(
    tester: SelectorTester,
    url: str,
    selectors_config: dict[str, Any],
    job_card_url: str,
) -> list[ElementResult]:
    """Run tests for per-selector-group configuration."""
    all_results: list[ElementResult] = []

    if "job_board" in selectors_config:
        job_board = selectors_config["job_board"]
        job_board_selectors = job_board.get("values", [])
        job_board_parser = ParserType[job_board.get("type", "default").upper()]
        print(f"\n{'=' * 80}")
        print("Testing JOB BOARD selectors...")
        results = await tester.test_selectors(
            url, job_board_selectors, job_board_parser
        )
        all_results.extend(results)

    if "job_card" in selectors_config:
        job_card = selectors_config["job_card"]
        job_card_selectors = job_card.get("values", [])
        job_card_parser = ParserType[job_card.get("type", "default").upper()]
        print(f"\n{'=' * 80}")
        print("Testing JOB CARD selectors...")
        results = await tester.test_selectors(
            job_card_url, job_card_selectors, job_card_parser
        )
        all_results.extend(results)

    return all_results


async def _run_per_selector_group_from_cli(
    tester: SelectorTester, args: argparse.Namespace
) -> list[ElementResult]:
    """Run tests for per-selector-group CLI arguments."""
    all_results: list[ElementResult] = []
    url = args.url

    if args.job_board_selectors:
        if not args.job_board_parser:
            print("Error: --job-board-parser is required with --job-board-selectors")
            sys.exit(1)
        job_board_parser = ParserType[args.job_board_parser.upper()]
        print(f"\n{'=' * 80}")
        print("Testing JOB BOARD selectors...")
        results = await tester.test_selectors(
            url, args.job_board_selectors, job_board_parser
        )
        all_results.extend(results)

    if args.job_card_selectors:
        if not args.job_card_parser:
            print("Error: --job-card-parser is required with --job-card-selectors")
            sys.exit(1)
        job_card_parser = ParserType[args.job_card_parser.upper()]
        print(f"\n{'=' * 80}")
        print("Testing JOB CARD selectors...")
        results = await tester.test_selectors(
            url, args.job_card_selectors, job_card_parser
        )
        all_results.extend(results)

    return all_results


def _get_exit_code(results: list[ElementResult]) -> int:
    """Determine exit code based on results."""
    if all(r.found for r in results):
        return 0  # All selectors found
    if any(r.found for r in results):
        return 1  # Some selectors found
    return 2  # No selectors found


async def main():
    """Main entry point for the selector tester tool."""
    parser = create_argument_parser()
    args = parser.parse_args()
    tester = SelectorTester(save_results=args.save, output_format=args.format)

    try:
        all_results = await _dispatch_test_mode(tester, args)
        sys.exit(_get_exit_code(all_results))
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(3)


async def _dispatch_test_mode(
    tester: SelectorTester, args: argparse.Namespace
) -> list[ElementResult]:
    """Dispatch to the appropriate test mode based on arguments."""
    # Config file mode
    if args.config:
        config = load_test_config(args.config)
        if not config:
            sys.exit(1)
        return await _run_from_config(tester, config)

    # Per-selector-group CLI mode
    if args.url and (args.job_board_selectors or args.job_card_selectors):
        return await _run_per_selector_group_from_cli(tester, args)

    # Simple CLI mode
    if args.url and args.selectors:
        parser_type = ParserType[args.parser.upper()]
        return await tester.test_selectors(args.url, args.selectors, parser_type)

    # Default test configuration
    logger.info("Using default test configuration")
    return await tester.test_selectors(
        "https://example.com", ["h1", "p", ".content"], ParserType.DEFAULT
    )


if __name__ == "__main__":
    asyncio.run(main())
