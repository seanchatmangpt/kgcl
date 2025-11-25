# CLI Refactor Notes

## Current State Assessment

- Each command (`daily_brief`, `weekly_retro`, `feature_list`, `query`, `config`) owns its own wiring for config loading, error messaging, and output formatting. Shared logic lives in `cli/utils.py`, but it mixes concerns (printing, config, clipboard, formatting) and relies heavily on side-effects.
- Dependency management is implicit. Commands instantiate ingestion/materialization/DSPy helpers directly, which makes testing hard and hides capabilities (e.g., no contract for LinkML validation or UNRDF access).
- Output handling is inconsistent across commands; some write markdown strings, others dump dicts, and JSON/table exports rely on callers to structure data correctly.
- Error handling is largely `print_error` with raw strings rather than structured receipts. Observability hooks (metrics/tracing) are absent from CLI flows despite being critical elsewhere.
- Configuration management is JSON-file based with little validation. There is no typed schema, making it easy to introduce invalid settings that only fail deep in command execution.

## Target Architecture

- **CliApp Core**: central orchestrator that wires shared services into commands. Provides lifecycle hooks (startup/shutdown), telemetry context, and consistent error handling.
- **Typed DTOs**: request/response objects per command (`DailyBriefRequest`, `WeeklyRetroRequest`, `FeatureListQuery`, `SparqlQueryRequest`, `ConfigSnapshot`). Responses embed metadata needed for formatting and receipts.
- **Service Protocols**:
  - `IngestionService`: fetches events/materialized features.
  - `DspyService`: executes DSPy signatures with fallback logic.
  - `SparqlService`: runs SPARQL queries with pagination/caching.
  - `ConfigService`: loads, validates, and persists CLI config.
  - `LinkmlValidator`: enforces schema compliance on inputs/outputs.
- **IO Abstractions**: `CliRenderer` handles markdown/table/json exports, `ClipboardGateway` encapsulates copy logic, `ReceiptEmitter` records structured outcomes.
- **Error Handling**: every command raises `CliCommandError` with sanitized payloads; `CliApp` catches, logs, and renders user-safe messages while preserving telemetry breadcrumbs.
- **Testing Strategy**: service protocols allow fast unit tests via fakes, while Click runner tests validate option parsing and output formatting end-to-end.

