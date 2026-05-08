#!/usr/bin/env python3
"""Validate the OAuth SDK conformance catalog.

Checks:
  1. Top-level structure (schema_version, catalog_id, catalog_version, etc.)
  2. Every case has every field listed in case_fields.required
  3. Case IDs are unique
  4. Every case's standard_refs entries exist in standards_in_scope ids
  5. Priority values are in the allowed enum

Exits 0 on success, 1 on any error.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

CATALOG = Path(__file__).resolve().parent.parent / "oauth-sdk-conformance-catalog.yaml"

TOP_LEVEL_SCHEMA: dict = {
    "type": "object",
    "required": [
        "schema_version",
        "catalog_id",
        "catalog_version",
        "standards_in_scope",
        "case_fields",
        "cases",
    ],
    "properties": {
        "schema_version": {"type": "string"},
        "catalog_id": {"type": "string", "minLength": 1},
        "catalog_version": {
            "type": "string",
            "pattern": r"^\d{4}-\d{2}-\d{2}$",
        },
        "source_baseline": {"type": "object"},
        "standards_in_scope": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "title", "status"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "status": {"type": "string", "minLength": 1},
                    "used_for": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "case_fields": {
            "type": "object",
            "required": ["required"],
            "properties": {
                "required": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
            },
        },
        "cases": {
            "type": "array",
            "minItems": 1,
        },
        "usage_guidance": {"type": "object"},
    },
}

CASE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PRIORITY_VALUES = {"critical", "high", "medium", "low"}


def fail(errors: list[str]) -> None:
    print("validate_catalog: FAIL", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not CATALOG.exists():
        fail([f"catalog not found at {CATALOG}"])

    with CATALOG.open() as f:
        data = yaml.safe_load(f)

    errors: list[str] = []

    # 1. Top-level schema
    validator = Draft202012Validator(TOP_LEVEL_SCHEMA)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema: {path}: {err.message}")

    if errors:
        fail(errors)

    required_fields: list[str] = data["case_fields"]["required"]
    standard_ids = {s["id"] for s in data["standards_in_scope"]}

    # 2, 3, 4, 5. Per-case checks
    seen_ids: Counter[str] = Counter()
    for idx, case in enumerate(data["cases"]):
        prefix = f"cases[{idx}]"
        cid = case.get("id", "<missing>")

        if not isinstance(case, dict):
            errors.append(f"{prefix}: not an object")
            continue

        # Required fields
        for field in required_fields:
            if field not in case:
                errors.append(f"{prefix} ({cid}): missing required field '{field}'")

        # ID format + uniqueness
        if "id" in case:
            if not isinstance(case["id"], str) or not CASE_ID_PATTERN.match(case["id"]):
                errors.append(f"{prefix}: id '{case['id']!r}' must match {CASE_ID_PATTERN.pattern}")
            seen_ids[case["id"]] += 1

        # Priority enum
        if "priority" in case and case["priority"] not in PRIORITY_VALUES:
            errors.append(
                f"{prefix} ({cid}): priority '{case['priority']}' not in {sorted(PRIORITY_VALUES)}"
            )

        # standard_refs must resolve
        if "standard_refs" in case:
            refs = case["standard_refs"]
            if not isinstance(refs, list) or not refs:
                errors.append(f"{prefix} ({cid}): standard_refs must be a non-empty list")
            else:
                for ref in refs:
                    if ref not in standard_ids:
                        errors.append(
                            f"{prefix} ({cid}): standard_refs entry '{ref}' "
                            f"not declared in standards_in_scope"
                        )

    # Duplicate case IDs
    for cid, count in seen_ids.items():
        if count > 1:
            errors.append(f"duplicate case id '{cid}' ({count} occurrences)")

    if errors:
        fail(errors)

    print(f"validate_catalog: OK ({len(data['cases'])} cases, {len(standard_ids)} standards)")


if __name__ == "__main__":
    main()
