from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class JobSite:
    code: str
    name: str


@dataclass
class MaterialCategory:
    key: str
    label: str
    description: str


@dataclass
class LaborActivity:
    key: str
    label: str
    description: str = ""
    default_quantity: float | None = None
    default_unit: str | None = None


@dataclass
class CompanyConfig:
    name: str
    employees: list[Employee] = field(default_factory=list)
    jobsites: list[JobSite] = field(default_factory=list)
    materials: list[MaterialCategory] = field(default_factory=list)
    labor_activities: list[LaborActivity] = field(default_factory=list)

    def employee_exists(self, name: str) -> bool:
        target = (name or "").strip().lower()
        return any((e.name or "").strip().lower() == target for e in self.employees)

    def find_jobsite(self, value: str) -> JobSite | None:
        v = (value or "").strip().lower()
        for js in self.jobsites:
            if js.code.strip().lower() == v or js.name.strip().lower() == v:
                return js
        return None

    def material_exists(self, key_or_label: str) -> bool:
        v = (key_or_label or "").strip().lower()
        for m in self.materials:
            if m.key.strip().lower() == v or m.label.strip().lower() == v:
                return True
        return False

    def find_labor_activity(self, key_or_label: str) -> LaborActivity | None:
        v = (key_or_label or "").strip().lower()
        for a in self.labor_activities:
            if a.key.strip().lower() == v or a.label.strip().lower() == v:
                return a
        return None


def load_company_config(path: str) -> CompanyConfig:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    name = str((data.get("company") or {}).get("name") or "")
    employees: list[Employee] = []
    for x in data.get("employees") or []:
        if isinstance(x, str):
            employees.append(Employee(name=x))
        elif isinstance(x, dict):
            employees.append(
                Employee(
                    name=str(x.get("name", "")),
                    role=(str(x.get("role")) if x.get("role") is not None else None),
                    apprentice_period=(
                        str(x.get("apprentice_period"))
                        if x.get("apprentice_period") is not None
                        else None
                    ),
                )
            )
    jobsites = [
        JobSite(code=str(x.get("code", "")), name=str(x.get("name", "")))
        for x in (data.get("jobsites") or [])
        if isinstance(x, dict)
    ]
    materials = [
        MaterialCategory(
            key=str(x.get("key", "")),
            label=str(x.get("label", "")),
            description=str(x.get("description", "")),
        )
        for x in (data.get("materials") or [])
        if isinstance(x, dict)
    ]
    labor_activities = [
        LaborActivity(
            key=str(x.get("key", "")),
            label=str(x.get("label", "")),
            description=str(x.get("description", "")),
            default_quantity=(
                float(x["default_quantity"]) if x.get("default_quantity") is not None else None
            ),
            default_unit=(str(x["default_unit"]) if x.get("default_unit") is not None else None),
        )
        for x in (data.get("labor_activities") or [])
        if isinstance(x, dict)
    ]
    return CompanyConfig(
        name=name,
        employees=employees,
        jobsites=jobsites,
        materials=materials,
        labor_activities=labor_activities,
    )


@dataclass
class Employee:
    name: str
    role: str | None = None  # e.g., Journeyman, Apprentice
    apprentice_period: str | None = None  # e.g., Year 1, Year 2


def load_from_env(default_path: str | None = None) -> CompanyConfig | None:
    """Load a company config from TIMESHEET_CONFIG_PATH or a default path."""
    path = os.environ.get("TIMESHEET_CONFIG_PATH") or default_path
    if not path:
        return None
    try:
        if not os.path.isfile(path):
            return None
        return load_company_config(path)
    except Exception:
        return None
