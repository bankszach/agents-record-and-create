# Timesheet Agent (Example)

This example demonstrates an agent that interactively gathers, validates, and exports crew timesheet entries. The agent asks clarifying questions to ensure completeness, supports text and optional voice input, streams UI updates for a supervisor to approve/correct, and finally exports a CSV for timekeepers.

Status: scaffolding only. This folder provides placeholders and interfaces for iterative development.

## Goals

- Interactive form-filling with validation and confirmations.
- Live progress updates (for UI to visualize and approve).
- Text-first UX with optional voice input.
- Deterministic CSV export for office workflows.

## Layout

- `backend/agent.py`: Orchestrates the fill → validate → confirm → revise loop.
- `backend/forms.py`: Timesheet schema and validation hooks.
- `backend/parsers.py`: Natural-language parsing to structured entries.
- `backend/exporters/csv.py`: CSV rendering with stable headers.
- `backend/io/voice.py`: Optional STT/TTS integration points (no deps in core example).
- `backend/server.py`: Placeholder for SSE/WebSocket updates to the UI.
- `ui/`: A lightweight web UI scaffold for live updates and approvals.

Note: The directory uses an underscore (`timesheet_agent`) so it is importable in tests.

## Running

Model-backed CLI demo (requires `OPENAI_API_KEY`):

```bash
export OPENAI_API_KEY=sk-...               # or set in your shell profile
export OPENAI_MODEL=gpt-4o-mini            # optional; defaults to gpt-4o-mini
uv run python -m examples.timesheet_agent.cli
```

Notes:
- Run as a module (`-m`) so relative imports resolve under the `examples` package. Running the file path directly will raise "attempted relative import with no known parent package".
- A `.env` file is optional; this example reads from environment variables. Use a shell export or your own dotenv loader if you prefer files.
- To automatically write the final CSV to disk, set `TIMESHEET_SAVE_PATH` in your environment or `.env`, e.g. `TIMESHEET_SAVE_PATH=./timesheet.csv`.
- For relative dates ("today", "yesterday"), the agent uses the `resolve_date` tool. You can set `TIMESHEET_TZ` (IANA name, e.g. `America/Los_Angeles`) and optionally `TIMESHEET_BASE_DATE` (YYYY-MM-DD) to anchor relative dates for testing.
- To classify hours, set `TIMESHEET_FULL_DAY_HOURS` (default `8`). The agent auto-annotates notes with `Partial day — Xh short of 8h` or `Overtime — +Xh over 8h` when hours differ.

### Tools

- `submit_entry(employee, date, hours, project?, notes?)`: Submit a single entry.
- `bulk_submit_entries(employees, date, hours, project?, notes?, notes_overrides?)`: Submit multiple entries that share date/hours/project. Use `notes_overrides` as a list of objects like `[{"employee": "Zach Banks", "note": "Reworked door plans"}]` to set per-person notes.
- `bulk_submit_entries(..., partial_overrides?)`: For part-time/left-early cases, provide `partial_overrides` as a list like `[{"employee": "Zach Banks", "other_site_hours": 2, "other_site_name": "Site B", "reason": "appointment"}]`. The tool will append a standardized note: `Partial day — Reason: appointment | Other site: 2h at Site B` (merged with any general note).
- `export_csv()`: Returns CSV for all submitted entries. If `TIMESHEET_SAVE_PATH` is set, also writes the CSV to that path.
- `resolve_date(phrase, timezone?, base_date?)`: Returns an ISO date string for natural phrases like `today`, `yesterday`, or `September 9 2025`.
 - `list_company_info()`: Returns configured employees (as names and detailed objects with `role` and `apprentice_period`), jobsites, material categories, and labor activities.
- `submit_labor_record(date, job, activity, quantity?, unit?, notes?)`: Record a labor activity for a jobsite. Validates against configured jobsites and activities. If `quantity`/`unit` are omitted, uses defaults from the config (e.g., Group Stretch & Flex = 0.25 hours).
- `export_labor_csv()`: Export recorded labor activities as CSV.
- `submit_material_record(date, job, category, quantity, unit, notes?)`: Record material usage for a jobsite (optional, if your workflow also tracks materials).
- `export_materials_csv()`: Export recorded materials as CSV.

### Company config

Provide a JSON config to predefine employees, jobsites, and material tracking categories. Set `TIMESHEET_CONFIG_PATH` in your environment or `.env` to point to your file. An example is included at:

- `examples/timesheet_agent/company.example.json`

Schema:

```json
{
  "company": { "name": "Acme Glazing" },
  "employees": [
    { "name": "Aaron Cole", "role": "Journeyman" },
    { "name": "Kevin Brooks", "role": "Apprentice", "apprentice_period": "Year 1" }
  ],
  "jobsites": [ { "code": "HQP", "name": "Headquarters Plaza" } ],
  "materials": [
    { "key": "metal", "label": "Metal", "description": "All metal framing, anchors, clips." },
    { "key": "glass", "label": "Glass", "description": "Insulated units, spandrel, lites." },
    { "key": "doors", "label": "Doors", "description": "Frames, slabs, hardware sets." },
    { "key": "other", "label": "Other", "description": "Miscellaneous consumables or site-specific." }
  ]
  ,
  "labor_activities": [
    { "key": "unit_install", "label": "Unit Install", "description": "Install units", "default_quantity": null, "default_unit": "hours" },
    { "key": "group_stretch", "label": "Group Stretch & Flex", "description": "Morning stretch/flex as a crew", "default_quantity": 0.25, "default_unit": "hours" },
    { "key": "safety_meeting", "label": "Safety Meeting", "description": "Tailgate/JSA", "default_quantity": 0.25, "default_unit": "hours" }
  ]
}
```

Set in `.env`:

```
TIMESHEET_CONFIG_PATH=./company.json
```
- Type natural language (e.g., “Alex 7.5 hours on 2025-09-01 for Project A”). The agent will ask follow-ups, then call tools to submit entries and finally export CSV when you say “done”.

## Next Steps

- Define minimal `TimesheetEntry` schema and basic validators.
- Implement a prompted loop skeleton in `agent.py` (no model calls yet).
- Add a thin event stream interface and wire a no-op server stub.
- Create a simple CLI demo to exercise the loop and CSV export.
- Expand unit tests and add snapshot tests for CSV and prompts.

Planned follow-ups:
- SSE/Web UI wired to stream events for live visualization and approvals.
- Optional voice support via `backend/io/voice.py` once the text path is solid.
Behavior notes
- Entries are upserted by `(employee, date)`. Re-submitting with a project later will update the existing entries rather than creating duplicates.
- When a company config is loaded and jobsites are defined, `project` is required and must match either a job code or job name in the config.
