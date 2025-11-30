"""
Main entry point for the job processing pipeline using Prefect.

This module provides a command-line interface and programmatic API
for running the job processing pipeline with Prefect orchestration.
"""

import asyncio

from pipeline.flows import main_pipeline_flow, sync_backend_flow


def run():
    """Run the complete job processing pipeline."""

    async def _run_pipeline():
        # Run the sync flow to ensure all companies exist in the backend
        await sync_backend_flow()

        # Run the main flow to process jobs
        await main_pipeline_flow()

    # Run the async pipeline
    asyncio.run(_run_pipeline())


if __name__ == "__main__":
    run()
