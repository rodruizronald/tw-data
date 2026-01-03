# Error Handling Guidelines

## Overview

This document defines the error handling architecture, policies, and patterns for the job processing pipeline. It serves as the authoritative reference for exception design, retry strategies, and error propagation across all layers.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Exception Hierarchy](#exception-hierarchy)
3. [Retry Policy](#retry-policy)
4. [Layer Responsibilities](#layer-responsibilities)
5. [Error Propagation Rules](#error-propagation-rules)
6. [Logging Standards](#logging-standards)
7. [Phase 2: Consistency Improvements](#phase-2-consistency-improvements)
8. [Phase 3: Robustness Improvements](#phase-3-robustness-improvements)
9. [Phase 4: Polish and Future Work](#phase-4-polish-and-future-work)

---

## Architecture Overview

### Pipeline Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN PIPELINE FLOW                        │
│  Orchestrates stages, handles critical failures, manages state   │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          STAGE FLOWS                             │
│  Coordinates tasks, manages concurrency, aggregates results      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PREFECT TASKS                            │
│  Retry decisions, Prefect integration, task-level error handling │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       STAGE PROCESSORS                           │
│  Business logic, metrics recording, exception transformation     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          SERVICES                                │
│  External integrations (OpenAI, Web, MongoDB, Supabase)          │
│  Primary exception source, retry logic for transient errors      │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Single Responsibility**: Each layer has one job regarding error handling
2. **Fail Fast**: Non-recoverable errors should propagate immediately
3. **Retry at Source**: Transient errors are retried closest to where they occur
4. **Context Preservation**: Error context is added once, not duplicated
5. **Graceful Degradation**: Individual failures shouldn't stop the entire pipeline

---

## Exception Hierarchy

### Pipeline Exceptions (`utils/exceptions.py`)

```
PipelineError (Base)
├── CompanyProcessingError      # Wrapper for unexpected errors
├── ConfigurationError          # Invalid configuration (non-retryable)
├── ValidationError             # Data validation failures (non-retryable)
├── FileOperationError          # File I/O errors (usually non-retryable)
├── WebExtractionError          # Web scraping failures (retryable)
├── OpenAIProcessingError       # OpenAI API errors (retryable)
└── DatabaseOperationError      # MongoDB errors (retryable)
```

### Supabase Exceptions (`data/supabase/exceptions.py`)

```
SupabaseBaseException (Base)
├── SupabaseConfigError         # Configuration errors (non-retryable)
├── SupabaseAuthError           # 401/403 errors (non-retryable)
├── SupabaseValidationError     # 400 errors (non-retryable)
├── SupabaseNotFoundError       # 404 errors (non-retryable)
├── SupabaseConflictError       # 409 errors (context-dependent)
├── SupabaseConnectionError     # Network errors (retryable)
│   ├── SupabaseTimeoutError    # Timeout errors (retryable)
│   └── SupabaseNetworkError    # Network failures (retryable)
├── SupabaseServerError         # 500+ errors (retryable)
├── SupabaseRateLimitError      # 429 errors (retryable)
├── SupabaseCircuitBreakerError # Circuit breaker open (retryable after delay)
└── SupabaseRetryExhaustedError # Max retries exceeded (non-retryable)
```

---

## Retry Policy

### Retryability Classification

Each exception type is classified as **retryable** or **non-retryable**:

| Exception                 | Retryable | Rationale                           |
| ------------------------- | --------- | ----------------------------------- |
| `ValidationError`         | ❌        | Bad data won't fix itself           |
| `ConfigurationError`      | ❌        | Requires code/config change         |
| `FileOperationError`      | ❌        | Usually permission/path issues      |
| `WebExtractionError`      | ✅        | Transient network/page load issues  |
| `OpenAIProcessingError`   | ✅        | Rate limits, timeouts are transient |
| `DatabaseOperationError`  | ✅        | Connection issues are transient     |
| `SupabaseAuthError`       | ❌        | Credentials won't fix themselves    |
| `SupabaseValidationError` | ❌        | Bad data structure                  |
| `SupabaseNotFoundError`   | ❌        | Resource doesn't exist              |
| `SupabaseConflictError`   | ⚠️        | Context-dependent (see below)       |
| `SupabaseConnectionError` | ✅        | Network issues are transient        |
| `SupabaseServerError`     | ✅        | Server may recover                  |
| `SupabaseRateLimitError`  | ✅        | Will succeed after backoff          |

### Conflict Error Handling

`SupabaseConflictError` (409) requires special handling:

- **Job already exists**: Not an error - skip silently
- **Technology already linked**: Not an error - skip silently
- **Other conflicts**: Log warning and continue

### Retry Strategy by Layer

| Layer              | Retry Mechanism   | Max Retries | Backoff                  |
| ------------------ | ----------------- | ----------- | ------------------------ |
| Services (OpenAI)  | Internal loop     | 3           | Exponential (1s, 2s, 4s) |
| Services (Web)     | Internal loop     | 4           | Linear (1s)              |
| Services (Metrics) | Internal loop     | 2           | Exponential (1s, 2s)     |
| Prefect Tasks      | Prefect `retries` | 0-2         | Fixed (30s)              |
| Flows              | None              | 0           | N/A                      |

**Important**: Service-level retries handle transient errors. Prefect task retries are for infrastructure-level failures that persist after service retries.

---

## Layer Responsibilities

### Services Layer

**Responsibility**: Execute operations, handle transient errors, raise typed exceptions

```python
# ✅ CORRECT: Service handles retries and raises typed exception
async def extract_html_content(self, url: str, ...) -> str:
    for attempt in range(self.config.max_retries + 1):
        try:
            # ... extraction logic ...
            return content
        except SomeTransientError:
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay)
                continue
            raise WebExtractionError(url, e, company_name, attempt + 1) from e
```

**Rules**:

- ✅ Implement retry logic for transient errors
- ✅ Raise domain-specific exceptions (not generic Exception)
- ✅ Include all relevant context in exception
- ❌ Don't log errors that will be logged upstream
- ❌ Don't catch and swallow exceptions silently

### Stage Processors Layer

**Responsibility**: Business logic, metrics recording, exception transformation

```python
# ✅ CORRECT: Stage processes and re-raises typed exceptions
async def process_single_company(self, company: CompanyData) -> list[Job]:
    try:
        return await self._execute_company_processing(company)
    except (WebExtractionError, OpenAIProcessingError) as e:
        self.logger.error(f"{type(e).__name__} - {e}")
        error_message = str(e)
        raise  # Re-raise for Prefect retry decision
    finally:
        self.metrics_service.record_stage_metrics(...)
```

**Rules**:

- ✅ Log errors with appropriate level (error for failures)
- ✅ Record metrics in `finally` block
- ✅ Re-raise retryable exceptions for upstream handling
- ✅ Transform unexpected exceptions to `CompanyProcessingError`
- ❌ Don't wrap already-typed exceptions (causes duplicate messages)
- ❌ Don't duplicate logging already done by services

### Prefect Tasks Layer

**Responsibility**: Retry decisions, Prefect integration

```python
# ✅ CORRECT: Task delegates to processor, handles Prefect concerns only
@task(retries=0, retry_delay_seconds=30)
async def process_job_listings_task(company: CompanyData, config: PipelineConfig) -> list[Job]:
    logger = get_run_logger()
    logger.info(f"Starting task for company: {company.name}")

    processor = Stage1Processor(config)
    return await processor.process_single_company(company)
```

**Rules**:

- ✅ Log task start/completion
- ✅ Let exceptions propagate for Prefect retry mechanism
- ❌ Don't duplicate logging already done by stages
- ❌ Don't catch and return empty list (masks failures)

### Stage Flows Layer

**Responsibility**: Concurrency control, result aggregation, task failure isolation

```python
# ✅ CORRECT: Flow isolates task failures, tracks results
async def process_with_semaphore(company, semaphore) -> TaskResult:
    async with semaphore:
        try:
            result = await process_job_listings_task(company, config)
            return TaskResult(success=True, data=result, company=company.name)
        except Exception as e:
            logger.error(f"Task failed for {company.name}: {e}")
            return TaskResult(success=False, error=str(e), company=company.name)
```

**Rules**:

- ✅ Use semaphores for concurrency control
- ✅ Isolate individual company failures
- ✅ Track success/failure status explicitly
- ❌ Don't let one company failure stop all companies

### Main Pipeline Flow

**Responsibility**: Stage orchestration, critical failure handling

```python
# ✅ CORRECT: Pipeline stops on critical stage failures
async def _execute_stage_1(...):
    try:
        results = await stage_1_flow(companies, config)
        return results
    except Exception as e:
        logger.error(f"Stage 1 failed: {e}")
        raise  # Critical failure - stop pipeline
```

**Rules**:

- ✅ Stop pipeline on critical stage failures
- ✅ Allow non-critical stages (e.g., metrics) to fail gracefully
- ❌ Don't swallow critical errors

---

## Error Propagation Rules

### Rule 1: Don't Double-Wrap Exceptions

```python
# ❌ WRONG: Creates duplicate error messages
except Exception as e:
    raise WebExtractionError(url, e, company_name) from e

# ✅ CORRECT: Check type first
except WebExtractionError:
    raise  # Already typed, re-raise as-is
except Exception as e:
    raise WebExtractionError(url, e, company_name) from e
```

### Rule 2: Add Context Once

```python
# ❌ WRONG: Context added at multiple layers
# Service: "Failed to connect to {url}"
# Stage: "Web extraction failed for {url}: Failed to connect to {url}"
# Task: "Error for {company}: Web extraction failed for {url}: ..."

# ✅ CORRECT: Context added at source only
# Service: raises WebExtractionError with all context
# Stage: logs and re-raises
# Task: lets it propagate
```

### Rule 3: Use Exception Chaining

```python
# ✅ CORRECT: Preserves original traceback
except SomeError as e:
    raise CustomError("message") from e

# ❌ WRONG: Loses original traceback
except SomeError as e:
    raise CustomError(f"message: {e}")
```

### Rule 4: Retryable Exceptions Must Propagate

```python
# ✅ CORRECT: Re-raise for retry mechanism
except WebExtractionError as e:
    self.logger.error(f"Extraction failed: {e}")
    raise  # Let Prefect retry

# ❌ WRONG: Swallows retryable error
except WebExtractionError as e:
    self.logger.error(f"Extraction failed: {e}")
    return []  # Lost retry opportunity
```

---

## Logging Standards

### Log Levels

| Level     | When to Use                       | Example                                                |
| --------- | --------------------------------- | ------------------------------------------------------ |
| `DEBUG`   | Detailed execution flow           | "Extracted content from selector: {selector}"          |
| `INFO`    | Normal operations, milestones     | "Processing 5 jobs for CompanyX"                       |
| `WARNING` | Recoverable issues, skipped items | "Technology 'React.js' not found, stored as unmatched" |
| `ERROR`   | Failures that affect results      | "Failed to process job: {title}"                       |

### Logging Rules

1. **Log Once**: Each error should be logged at exactly one layer
2. **Include Context**: Company name, job title, URL as appropriate
3. **No Sensitive Data**: Never log API keys, passwords, or PII
4. **Structured Where Possible**: Use f-strings with clear field names

### Which Layer Logs What

| Layer    | Logs                                                 |
| -------- | ---------------------------------------------------- |
| Services | DEBUG for operations, WARNING for retries            |
| Stages   | INFO for progress, ERROR for failures                |
| Tasks    | INFO for start/completion only                       |
| Flows    | INFO for stage transitions, ERROR for stage failures |

---

## Phase 2: Consistency Improvements

### Goals

1. Establish clear layer responsibilities (reduce duplicate handling)
2. Add `retryable` attribute to exception classes
3. Remove unused exception imports
4. Standardize exception handling patterns across all stages

### Changes

#### 2.1 Add Retryable Attribute to Exceptions

Modify `utils/exceptions.py` to add a class-level `retryable` attribute:

```python
class PipelineError(Exception):
    """Base exception for all pipeline operations."""
    retryable: bool = False  # Default to non-retryable

class WebExtractionError(PipelineError):
    retryable = True

class OpenAIProcessingError(PipelineError):
    retryable = True

class DatabaseOperationError(PipelineError):
    retryable = True

class ValidationError(PipelineError):
    retryable = False
```

#### 2.2 Simplify Task Exception Handling

Reduce tasks to single pattern using `retryable` attribute:

```python
@task(retries=2, retry_delay_seconds=30)
async def process_job_listings_task(company: CompanyData, config: PipelineConfig) -> list[Job]:
    logger = get_run_logger()
    logger.info(f"Starting task for company: {company.name}")

    processor = Stage1Processor(config)
    try:
        return await processor.process_single_company(company)
    except PipelineError as e:
        if e.retryable:
            raise  # Trigger Prefect retry
        logger.error(f"Non-retryable error for {company.name}: {e}")
        return []
```

#### 2.3 Remove Unused Exception Imports

Clean up imports in task files to only include exceptions actually raised by corresponding stages:

| File              | Remove                                                        |
| ----------------- | ------------------------------------------------------------- |
| `stage_2_task.py` | `FileOperationError`, `ValidationError`                       |
| `stage_3_task.py` | `FileOperationError`, `ValidationError`                       |
| `stage_4_task.py` | `FileOperationError`, `ValidationError`, `WebExtractionError` |

#### 2.4 Standardize Stage Exception Handling

Ensure all stages follow the same pattern for the main `process_*` method:

```python
async def process_jobs(self, jobs: list[Job], company_name: str) -> list[Job]:
    # ... setup ...
    try:
        # ... processing ...
        return processed_jobs
    except DatabaseOperationError:
        raise  # Retryable - propagate
    except Exception as e:
        self.logger.error(f"Error processing jobs for {company_name}: {e}")
        error_message = str(e)
        status = StageStatus.FAILED
        return []
    finally:
        # Always record metrics
        self._record_metrics(...)
```

---

## Phase 3: Robustness Improvements

### Goals

1. Protect metrics recording from masking original errors
2. Improve flow-level error visibility
3. Add result type pattern for better failure tracking

### Changes

#### 3.1 Protect Metrics Recording in Finally Blocks

Wrap metrics recording in its own try/except:

```python
finally:
    try:
        self.metrics_service.record_stage_metrics(
            company_name=company_name,
            stage=self.config.stage_X.tag,
            metrics_input=metrics_input,
        )
    except Exception as metrics_error:
        self.logger.warning(f"Failed to record metrics: {metrics_error}")
        # Don't re-raise - metrics failure shouldn't mask the original error
```

#### 3.2 Introduce TaskResult Type

Create a result type to distinguish between "no results" and "failure":

```python
# core/models/results.py
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')

@dataclass
class TaskResult(Generic[T]):
    """Result container for task execution."""
    success: bool
    data: T | None = None
    error: str | None = None
    company_name: str = ""

    @classmethod
    def ok(cls, data: T, company_name: str) -> "TaskResult[T]":
        return cls(success=True, data=data, company_name=company_name)

    @classmethod
    def fail(cls, error: str, company_name: str) -> "TaskResult[T]":
        return cls(success=False, error=error, company_name=company_name)
```

#### 3.3 Update Flow Result Aggregation

Modify flows to use `TaskResult` for clearer status tracking:

```python
async def process_with_semaphore(company, semaphore) -> TaskResult[list[Job]]:
    async with semaphore:
        try:
            jobs_data = db_service.load_jobs_for_stage(company.name, config.stage_X.tag)
            if not jobs_data:
                return TaskResult.ok([], company.name)  # Success with no data

            result = await process_job_task(company, jobs_data, config)
            return TaskResult.ok(result, company.name)
        except Exception as e:
            logger.error(f"Task failed for {company.name}: {e}")
            return TaskResult.fail(str(e), company.name)

# After gathering results
successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]
logger.info(f"Completed: {len(successful)} successful, {len(failed)} failed")
```

---

## Phase 4: Polish and Future Work

### Goals

1. Standardize error message format
2. Consider structured logging
3. Add error categorization for dashboards

### Changes

#### 4.1 Standardize Error Message Format

Adopt consistent format: `[Context] Action failed: Reason`

```python
# Format for all exception messages
f"[{company_name}] {action} failed: {reason}"

# Examples
"[Akurey] Web extraction failed: No content found for selector"
"[Akurey] OpenAI processing failed: Rate limit exceeded"
"[Akurey] Database operation 'save_stage_results' failed: Connection timeout"
```

#### 4.2 Structured Logging (Future)

Consider adding structured context for log aggregation:

```python
logger.error(
    "Web extraction failed",
    extra={
        "company": company_name,
        "url": url,
        "retry_attempt": attempt,
        "error_type": type(e).__name__,
        "stage": "stage_1",
    }
)
```

#### 4.3 Error Categorization (Future)

Add error categories for dashboard filtering:

```python
class ErrorCategory(str, Enum):
    NETWORK = "network"        # Connection, timeout issues
    RATE_LIMIT = "rate_limit"  # API rate limiting
    DATA = "data"              # Validation, parsing errors
    AUTH = "auth"              # Authentication failures
    INFRASTRUCTURE = "infra"   # Database, service unavailable
```

---

## Quick Reference

### Exception Handling Checklist

- [ ] Is the exception typed correctly? (not generic `Exception`)
- [ ] Is context added exactly once? (not duplicated)
- [ ] Is the exception chained with `from e`?
- [ ] Are retryable exceptions being re-raised?
- [ ] Is logging happening at the right layer?
- [ ] Are metrics protected in a `finally` block?

### When to Use Each Exception

| Scenario                    | Exception                |
| --------------------------- | ------------------------ |
| Web page won't load         | `WebExtractionError`     |
| Selector finds no content   | `WebExtractionError`     |
| OpenAI returns error        | `OpenAIProcessingError`  |
| OpenAI returns invalid JSON | `OpenAIProcessingError`  |
| MongoDB connection fails    | `DatabaseOperationError` |
| MongoDB write fails         | `DatabaseOperationError` |
| Invalid company config      | `ValidationError`        |
| Missing required field      | `ValidationError`        |
| Prompt file not found       | `FileOperationError`     |
| Unexpected error in stage   | `CompanyProcessingError` |

---

## Version History

| Version | Date       | Changes         |
| ------- | ---------- | --------------- |
| 1.0     | 2024-XX-XX | Initial version |
