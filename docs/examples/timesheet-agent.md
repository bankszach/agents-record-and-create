# Timesheet Agent Example

This document tracks the design and evolution of the timesheet agent example located in `examples/timesheet_agent/`.

## Scope

- Interactive acquisition of timesheet entries from a project lead.
- Validation loop with targeted follow-ups for missing fields.
- Supervisor approval and correction before export.
- Deterministic CSV export for handoff to timekeepers.

## Architecture Sketch

- Agent loop in `backend/agent.py` emits events for the UI.
- Schema/validation in `backend/forms.py`.
- Freeform parsing in `backend/parsers.py`.
- CSV export in `backend/exporters/csv.py`.
- Optional voice interfaces in `backend/io/voice.py`.
- Streaming transport stub in `backend/server.py`.

## Open Questions

- Event protocol: which event types and payload shape should be standardized for reuse across examples.
- Validation adapters: when to introduce pydantic or keep dataclasses + helpers.
- Voice dependencies: keep optional to avoid burdening the SDK.

## Testing Strategy

- Unit tests for CSV export, schema validation, and parser edge cases.
- Snapshot tests for prompts and event sequences once the loop is implemented.

