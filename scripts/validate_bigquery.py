#!/usr/bin/env python3
"""Validate BigQuery naming and metadata conventions for repository SQL."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BIGQUERY_DIR = ROOT / "BigQuery"
DATASETS_DIR = BIGQUERY_DIR / "DATASETS"
IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*$")
TABLE_PATTERN = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:EXTERNAL\s+)?TABLE\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?(`?[\w.-]+`?)",
    re.IGNORECASE,
)
ROUTINE_PATTERN = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+"
    r"(`?[\w.-]+`?)",
    re.IGNORECASE,
)
SCHEMA_PATTERN = re.compile(
    r"\bCREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+([A-Za-z0-9_]+)",
    re.IGNORECASE,
)


def normalize_sql(text: str) -> str:
    return text.translate(
        str.maketrans(
            {
                "\u00a0": " ",
                "\u2007": " ",
                "\u202f": " ",
            }
        )
    )


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    parens = 0
    angles = 0
    quote: str | None = None
    index = 0

    while index < len(text):
        char = text[index]
        if quote:
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
        elif char == "<":
            angles += 1
        elif char == ">":
            angles = max(0, angles - 1)
        elif char == "," and parens == 0 and angles == 0:
            parts.append(text[start:index])
            start = index + 1
        index += 1

    parts.append(text[start:])
    return parts


def find_matching_paren(text: str, open_index: int) -> int | None:
    depth = 0
    quote: str | None = None
    index = open_index

    while index < len(text):
        char = text[index]
        if quote:
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def object_name(qualified_name: str) -> str:
    return qualified_name.strip("`").split(".")[-1]


def validate_dataset(path: Path, errors: list[str]) -> str | None:
    sql = normalize_sql(path.read_text(encoding="utf-8-sig"))
    match = SCHEMA_PATTERN.search(sql)
    if not match:
        errors.append(f"{path.relative_to(ROOT)}: expected CREATE SCHEMA IF NOT EXISTS")
        return None

    name = match.group(1)
    if not IDENTIFIER.fullmatch(name):
        errors.append(f"{path.relative_to(ROOT)}: dataset name {name!r} must be uppercase")
    if name != path.stem:
        errors.append(f"{path.relative_to(ROOT)}: dataset name must match file name {path.stem!r}")
    options = sql[match.end() :]
    if not re.search(r"\blocation\s*=\s*['\"]us-central1['\"]", options, re.IGNORECASE):
        errors.append(f"{path.relative_to(ROOT)}: dataset location must be us-central1")
    if not re.search(r"\bdescription\s*=\s*['\"][^'\"]+['\"]", options, re.IGNORECASE):
        errors.append(f"{path.relative_to(ROOT)}: dataset description is required")
    return name


def validate_table(path: Path, errors: list[str]) -> str | None:
    sql = normalize_sql(path.read_text(encoding="utf-8-sig"))
    match = TABLE_PATTERN.search(sql)
    relative = path.relative_to(ROOT)
    if not match:
        errors.append(f"{relative}: expected a CREATE TABLE statement")
        return None

    name = object_name(match.group(1))
    if not IDENTIFIER.fullmatch(name):
        errors.append(f"{relative}: table name {name!r} must be uppercase")
    if name != path.stem:
        errors.append(f"{relative}: table name must match file name {path.stem!r}")
    declaration = sql[match.start() : match.end()]
    if re.search(r"\bCREATE\s+OR\s+REPLACE\s+TABLE\b", declaration, re.IGNORECASE):
        errors.append(
            f"{relative}: CREATE OR REPLACE TABLE can overwrite stored data; use a reviewed migration"
        )

    open_index = sql.find("(", match.end())
    if open_index < 0:
        errors.append(f"{relative}: table column schema is required")
        return name
    close_index = find_matching_paren(sql, open_index)
    if close_index is None:
        errors.append(f"{relative}: could not parse table column schema")
        return name

    columns = split_top_level(sql[open_index + 1 : close_index])
    for column in columns:
        column = column.strip()
        column_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+", column)
        if not column_match:
            errors.append(f"{relative}: could not identify a column in {column[:50]!r}")
            continue
        column_name = column_match.group(1)
        if not IDENTIFIER.fullmatch(column_name):
            errors.append(f"{relative}: column name {column_name!r} must be uppercase")
        if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", column, re.IGNORECASE | re.DOTALL):
            errors.append(f"{relative}: column {column_name} requires a description")

    table_options = sql[close_index + 1 :]
    if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", table_options, re.IGNORECASE | re.DOTALL):
        errors.append(f"{relative}: table description is required in OPTIONS")
    return name


def validate_routine(path: Path, errors: list[str]) -> None:
    sql = normalize_sql(path.read_text(encoding="utf-8-sig"))
    match = ROUTINE_PATTERN.search(sql)
    relative = path.relative_to(ROOT)
    if not match:
        errors.append(f"{relative}: expected a CREATE PROCEDURE or CREATE FUNCTION statement")
        return
    name = object_name(match.group(1))
    if not IDENTIFIER.fullmatch(name):
        errors.append(f"{relative}: routine name {name!r} must be uppercase")
    if name != path.stem:
        errors.append(f"{relative}: routine name must match file name {path.stem!r}")


def main() -> int:
    errors: list[str] = []
    dataset_names = {
        name
        for path in sorted(DATASETS_DIR.glob("*.sql"))
        if (name := validate_dataset(path, errors)) is not None
    }

    table_files = sorted(BIGQUERY_DIR.glob("*/TABLES/*.sql"))
    routine_files = sorted(BIGQUERY_DIR.glob("*/ROUTINES/*.sql"))
    required_datasets = {path.parent.parent.name for path in table_files + routine_files}
    for dataset in sorted(required_datasets - dataset_names):
        errors.append(f"BigQuery/DATASETS: missing dataset definition for {dataset}")

    for path in table_files:
        validate_table(path, errors)
    for path in routine_files:
        validate_routine(path, errors)

    if errors:
        print("BigQuery standards validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"BigQuery standards validation passed "
        f"({len(dataset_names)} datasets, {len(table_files)} tables, {len(routine_files)} routines)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
