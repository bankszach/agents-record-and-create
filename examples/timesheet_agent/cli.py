from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from typing_extensions import NotRequired, TypedDict

from agents import Agent, ModelSettings, RunContextWrapper, function_tool, run_demo_loop

from .backend.config import CompanyConfig, load_from_env
from .backend.exporters.csv import render_csv
from .backend.forms import from_dict as entry_from_dict, validate as validate_entry
from .backend.parsers import resolve_date_phrase
from .backend.utils import classify_hours, get_full_day_hours, merge_notes


def _fallback_load_dotenv() -> None:
    """Lightweight .env loader to support local dev without extra deps.

    - Loads from CWD/.env and repo_root/.env (repo_root relative to this file).
    - Does not override variables already set in the environment.
    - Supports simple KEY=VALUE lines; ignores comments and blanks.
    """
    candidates: list[str] = []
    try:
        here = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
        candidates = [os.path.join(os.getcwd(), ".env"), os.path.join(repo_root, ".env")]
    except Exception:
        candidates = [os.path.join(os.getcwd(), ".env")]

    for path in candidates:
        try:
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            # Non-fatal; continue to next candidate.
            continue


try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    _fallback_load_dotenv()


@dataclass
class TimesheetContext:
    """Per-run context to store collected entries."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    materials: list[dict[str, Any]] = field(default_factory=list)
    labor: list[dict[str, Any]] = field(default_factory=list)
    config: CompanyConfig | None = None


@function_tool
def submit_entry(
    ctx: RunContextWrapper[TimesheetContext],
    employee: str,
    date: str,
    hours: float,
    project: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Submit a single timesheet entry once all required fields are known.

    Args:
        employee: Full name exactly as on the roster.
        date: Work date in YYYY-MM-DD format.
        hours: Hours worked as a decimal (e.g., 7.5).
        project: Optional short code or project name.
        notes: Optional freeform notes for payroll.
    """
    entry = entry_from_dict(
        {
            "employee": employee,
            "date": date,
            "hours": hours,
            "project": project,
            "notes": notes,
        }
    )
    problems = validate_entry(entry)
    # Config validation: check employee and project against config lists if present.
    if hasattr(ctx.context, "config") and ctx.context.config:
        cfg = ctx.context.config
        if entry.employee and not cfg.employee_exists(entry.employee):
            problems.append(f"Unknown employee: {entry.employee} (not in roster)")
        # If company has jobsites configured, require a project field.
        if cfg.jobsites and not entry.project:
            problems.append("Project is required (company has configured jobsites).")
        if entry.project:
            if not cfg.find_jobsite(entry.project):
                problems.append(f"Unknown jobsite/project: {entry.project} (not in config)")
    if problems:
        return {"status": "error", "problems": problems}
    # Auto-annotate overtime/partial day
    classif = classify_hours(entry.hours, get_full_day_hours())
    final_notes = merge_notes(entry.notes, [classif])
    _upsert_entry(
        ctx.context.entries,
        employee=entry.employee,
        date=entry.date,
        hours=entry.hours,
        project=entry.project,
        notes=final_notes,
    )
    return {
        "status": "ok",
        "count": len(ctx.context.entries),
        "entry": {
            **entry.__dict__,
            "notes": final_notes,
        },
    }


@function_tool
def export_csv(ctx: RunContextWrapper[TimesheetContext]) -> str:
    """Export all submitted entries as CSV with headers: employee,date,hours,project,notes."""
    headers = ["employee", "date", "hours", "project", "notes"]
    csv_text = render_csv(ctx.context.entries, headers)
    save_path = os.environ.get("TIMESHEET_SAVE_PATH")
    if save_path:
        try:
            folder = os.path.dirname(save_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(csv_text)
        except Exception:
            # Silently ignore write errors to keep tool output strictly CSV content.
            pass
    return csv_text


@function_tool
def resolve_date(phrase: str, timezone: str | None = None, base_date: str | None = None) -> str:
    """Resolve a relative or natural-language date to ISO YYYY-MM-DD.

    Args:
        phrase: A date like "today", "yesterday", or "September 9 2025".
        timezone: Optional IANA timezone (e.g., America/Los_Angeles). Defaults to env TIMESHEET_TZ or system tz.
        base_date: Optional YYYY-MM-DD used as an anchor for relative phrases (tests/reproducibility).
    Returns:
        ISO date string (YYYY-MM-DD), or empty string if not understood.
    """
    tz = timezone or os.environ.get("TIMESHEET_TZ")
    base = base_date or os.environ.get("TIMESHEET_BASE_DATE")
    return resolve_date_phrase(phrase, timezone=tz, base_date=base)


class NoteOverride(TypedDict):
    """Specifies a per-person note override.

    Fields:
        employee: Full name to match exactly against the submitted employees.
        note: Override note text for that employee.
    """

    employee: str
    note: str


class PartialOverride(TypedDict):
    """Per-person partial-day details used to generate consistent notes.

    Fields:
        employee: Full name (required).
        other_site_hours: Optional float for hours spent on another site.
        other_site_name: Optional name/code of the other site.
        reason: Optional text (e.g., "sick", "appointment", "left early").
    """

    employee: str
    other_site_hours: NotRequired[float]
    other_site_name: NotRequired[str]
    reason: NotRequired[str]


@function_tool
def bulk_submit_entries(
    ctx: RunContextWrapper[TimesheetContext],
    employees: list[str],
    date: str,
    hours: float,
    project: str | None = None,
    notes: str | None = None,
    notes_overrides: list[NoteOverride] | None = None,
    partial_overrides: list[PartialOverride] | None = None,
) -> dict[str, Any]:
    """Submit multiple timesheet entries that share date/hours/project.

    Args:
        employees: List of employee full names to add.
        date: Work date in YYYY-MM-DD format applied to all.
        hours: Hours worked as a decimal applied to all.
        project: Optional project code/name applied to all.
        notes: Optional general notes applied to all (can be overridden per person).
        notes_overrides: Optional list of per-person note overrides with fields `employee` and `note`.
        partial_overrides: Optional list for per-person partial-day details. Fields:
            - employee (required)
            - other_site_hours (optional float)
            - other_site_name (optional string)
            - reason (optional string; e.g., "sick", "appointment", "left early").
    """
    added = 0
    problems_all: list[dict[str, Any]] = []
    override_map: dict[str, str] = {
        o["employee"]: o["note"]
        for o in (notes_overrides or [])
        if o.get("employee") and o.get("note")
    }
    partial_map: dict[str, PartialOverride] = {
        p["employee"]: p for p in (partial_overrides or []) if p.get("employee")
    }
    full_day = get_full_day_hours()
    for emp in employees or []:
        base_note = override_map.get(emp, notes)
        # Compose partial-day note if provided
        p = partial_map.get(emp)
        partial_note = None
        if p:
            parts: list[str] = []
            reason = p.get("reason")
            if reason:
                parts.append(f"Reason: {reason}")
            osh = p.get("other_site_hours")
            osn = p.get("other_site_name")
            if osh is not None:
                if osn:
                    parts.append(f"Other site: {osh}h at {osn}")
                else:
                    parts.append(f"Other site: {osh}h")
            if parts:
                partial_note = "Partial day — " + " | ".join(parts)
        # Classification based on hours
        classif = classify_hours(hours, full_day)
        # Merge notes: base, partial, classification
        note = merge_notes(base_note, [partial_note, classif])
        entry = entry_from_dict(
            {
                "employee": emp,
                "date": date,
                "hours": hours,
                "project": project,
                "notes": note,
            }
        )
        problems = validate_entry(entry)
        if hasattr(ctx.context, "config") and ctx.context.config:
            cfg = ctx.context.config
            if entry.employee and not cfg.employee_exists(entry.employee):
                problems.append(f"Unknown employee: {entry.employee} (not in roster)")
            if cfg.jobsites and not entry.project:
                problems.append("Project is required (company has configured jobsites).")
            if entry.project and not cfg.find_jobsite(entry.project):
                problems.append(f"Unknown jobsite/project: {entry.project} (not in config)")
        if problems:
            problems_all.append({"employee": emp, "problems": problems})
            continue
        _upsert_entry(
            ctx.context.entries,
            employee=entry.employee,
            date=entry.date,
            hours=entry.hours,
            project=entry.project,
            notes=entry.notes,
        )
        added += 1
    status = "ok" if added and not problems_all else ("partial" if added else "error")
    return {
        "status": status,
        "added": added,
        "count": len(ctx.context.entries),
        "issues": problems_all,
    }


def _upsert_entry(
    entries: list[dict[str, Any]],
    *,
    employee: str,
    date: str,
    hours: float,
    project: str | None,
    notes: str | None,
) -> None:
    """Insert or update an entry by (employee, date).

    - If an entry matches on (employee, date), update hours, project (if provided),
      and merge notes. Otherwise append a new entry.
    - Preserves list order for stable CSV output (updates in place).
    """
    idx = next(
        (
            i
            for i, r in enumerate(entries)
            if r.get("employee") == employee and r.get("date") == date
        ),
        -1,
    )
    if idx >= 0:
        existing = entries[idx]
        existing["hours"] = hours
        if project:
            existing["project"] = project
        # Merge notes, de-duplicating
        existing["notes"] = merge_notes(existing.get("notes"), [notes])
        entries[idx] = existing
    else:
        entries.append(
            {
                "employee": employee,
                "date": date,
                "hours": hours,
                "project": project,
                "notes": notes,
            }
        )


@function_tool
def list_company_info(ctx: RunContextWrapper[TimesheetContext]) -> dict[str, Any]:
    """Return configured employees, jobsites, and material categories for validation and lookup."""
    cfg = ctx.context.config
    if not cfg:
        return {"status": "empty", "employees": [], "jobsites": [], "materials": []}
    return {
        "status": "ok",
        "employees": [e.name for e in cfg.employees],
        "employees_detailed": [
            {"name": e.name, "role": e.role, "apprentice_period": e.apprentice_period}
            for e in cfg.employees
        ],
        "jobsites": [{"code": j.code, "name": j.name} for j in cfg.jobsites],
        "materials": [
            {"key": m.key, "label": m.label, "description": m.description} for m in cfg.materials
        ],
        "labor_activities": [
            {
                "key": a.key,
                "label": a.label,
                "description": a.description,
                "default_quantity": a.default_quantity,
                "default_unit": a.default_unit,
            }
            for a in cfg.labor_activities
        ],
    }


@function_tool
def submit_material_record(
    ctx: RunContextWrapper[TimesheetContext],
    date: str,
    job: str,
    category: str,
    quantity: float,
    unit: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Submit a material usage record for a jobsite.

    Args:
        date: Work date in YYYY-MM-DD.
        job: Job code or name (must match config).
        category: One of the configured material categories (key or label).
        quantity: Numeric amount.
        unit: Unit string (e.g., pcs, lf, sf, sets).
        notes: Optional notes.
    """
    cfg = ctx.context.config
    problems: list[str] = []
    if cfg:
        jobsite = cfg.find_jobsite(job)
        if not jobsite:
            problems.append(f"Unknown jobsite: {job}")
        if not cfg.material_exists(category):
            problems.append(f"Unknown material category: {category}")
    if not date:
        problems.append("Date is required.")
    if quantity is None or quantity <= 0:
        problems.append("Quantity must be greater than zero.")
    if not unit:
        problems.append("Unit is required.")
    if problems:
        return {"status": "error", "problems": problems}
    rec = {
        "date": date,
        "job": job,
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "notes": notes,
    }
    ctx.context.materials.append(rec)
    return {"status": "ok", "count": len(ctx.context.materials), "record": rec}


@function_tool
def export_materials_csv(ctx: RunContextWrapper[TimesheetContext]) -> str:
    """Export submitted material records as CSV with headers: date,job,category,quantity,unit,notes."""
    headers = ["date", "job", "category", "quantity", "unit", "notes"]
    return render_csv(ctx.context.materials, headers)


@function_tool
def submit_labor_record(
    ctx: RunContextWrapper[TimesheetContext],
    date: str,
    job: str,
    activity: str,
    quantity: float | None = None,
    unit: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Submit a labor activity record for a jobsite.

    - Validates job and activity against config.
    - If quantity or unit is omitted, uses activity defaults when available.
    """
    cfg = ctx.context.config
    problems: list[str] = []
    default_qty: float | None = None
    default_unit: str | None = None
    if cfg:
        jobsite = cfg.find_jobsite(job)
        if not jobsite:
            problems.append(f"Unknown jobsite: {job}")
        act = cfg.find_labor_activity(activity)
        if not act:
            problems.append(f"Unknown labor activity: {activity}")
        else:
            default_qty = act.default_quantity
            default_unit = act.default_unit
    # Apply defaults if not provided
    qty = quantity if quantity is not None else default_qty
    u = unit if unit is not None else default_unit
    if not date:
        problems.append("Date is required.")
    if qty is None or qty <= 0:
        problems.append("Quantity must be greater than zero (or set a default in config).")
    if not u:
        problems.append("Unit is required (or set a default in config).")
    if problems:
        return {"status": "error", "problems": problems}
    rec = {
        "date": date,
        "job": job,
        "activity": activity,
        "quantity": qty,
        "unit": u,
        "notes": notes,
    }
    ctx.context.labor.append(rec)
    return {"status": "ok", "count": len(ctx.context.labor), "record": rec}


@function_tool
def export_labor_csv(ctx: RunContextWrapper[TimesheetContext]) -> str:
    """Export submitted labor activity records as CSV with headers: date,job,activity,quantity,unit,notes."""
    headers = ["date", "job", "activity", "quantity", "unit", "notes"]
    return render_csv(ctx.context.labor, headers)


def build_agent(model_name: str) -> Agent[TimesheetContext]:
    instructions = (
        "You are a meticulous timesheet assistant for a project lead. "
        "Gather timesheet entries through a short dialogue. Your goal is to capture, one entry at a time, "
        "the following fields: employee (full name), date (YYYY-MM-DD), hours (decimal), project (short code/name), notes (optional). "
        "Ask targeted follow-up questions whenever required fields are missing or ambiguous; do not invent values. "
        "When you have all required fields for a single entry, call the submit_entry tool with all fields. "
        "If the user provides multiple employees that share the same date/hours/project, prefer calling the bulk_submit_entries tool. "
        "You may pass a general 'notes' plus specific 'notes_overrides' as a list of objects with fields 'employee' and 'note' for per-person notes. "
        "When someone is part-time/left early, ask whether they spent time on another site and how many hours, or why they left (e.g., sick/appointment). "
        "Include these details via 'partial_overrides' so the note reads like: 'Partial day — Reason: sick | Other site: 2h at M567'. "
        "When the user mentions a relative or natural-language date (e.g., 'today', 'yesterday', 'September 9 2025'), use the resolve_date tool to convert it to YYYY-MM-DD based on the local timezone; do not guess. "
        "Validate employees against the configured roster and projects against configured jobsites. If unknown, ask to confirm or correct. "
        "You can use list_company_info to see the roster, jobsites, and both material categories and labor activities. "
        "For labor tracking (e.g., Unit Install, Group Stretch & Flex), use submit_labor_record with job, activity, quantity, and unit. If the company config provides defaults (e.g., group stretch = 0.25 hours), use those when not specified. When asked, use export_labor_csv to provide a CSV. "
        "After a successful submission, briefly acknowledge and ask if there is another entry. "
        "When the user indicates they are done, call export_csv and return only the CSV content as your final response. "
        "Be concise and ask one question at a time."
    )

    return Agent[TimesheetContext](
        name="Timesheet Agent",
        instructions=instructions,
        tools=[
            list_company_info,
            resolve_date,
            submit_entry,
            bulk_submit_entries,
            submit_labor_record,
            export_labor_csv,
            submit_material_record,
            export_materials_csv,
            export_csv,
        ],
        model=model_name,
        model_settings=ModelSettings(),
    )


async def main() -> None:
    # Model selection (default keeps compatibility with SDK defaults if unset)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Basic check for API key; the SDK also checks env during first call
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY is not set. Set it in your shell or a .env loader.")

    agent = build_agent(model)
    print("Timesheet Agent ready. Type entries or 'done' when finished. Ctrl+C to exit.")

    # Persist run context across turns
    context = TimesheetContext()
    # Load company config once per session.
    context.config = load_from_env(
        default_path=os.path.join(os.path.dirname(__file__), "company.example.json")
    )
    await run_demo_loop(agent, stream=True, context=context)


if __name__ == "__main__":
    asyncio.run(main())
