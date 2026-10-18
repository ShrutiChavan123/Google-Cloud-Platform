from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*$")
OBJECT_NAME = r"`?[\w.-]+`?"

TABLE_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:EXTERNAL\s+)?TABLE\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?({OBJECT_NAME})",
    re.IGNORECASE,
)
VIEW_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+({OBJECT_NAME})",
    re.IGNORECASE,
)
PROCEDURE_RE = re.compile(
    rf"\bCREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+({OBJECT_NAME})",
    re.IGNORECASE,
)
DATASET_RE = re.compile(
    r"\bCREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+([A-Za-z0-9_]+)",
    re.IGNORECASE,
)
COMMENTED_SQL_RE = re.compile(
    r"\b(?:"
    r"SELECT\s+.+?\s+FROM\b|"
    r"INSERT\s+INTO\b|"
    r"UPDATE\s+\S+\s+SET\b|"
    r"DELETE\s+FROM\b|"
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|PROCEDURE|FUNCTION)\b|"
    r"DROP\s+(?:TABLE|VIEW|PROCEDURE|FUNCTION)\b|"
    r"ALTER\s+TABLE\b|"
    r"MERGE\s+INTO\b|"
    r"TRUNCATE\s+TABLE\b|"
    r"CALL\s+[\w.`]+|"
    r"BEGIN\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
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


def object_parts(name: str) -> list[str]:
    return name.strip("`").split(".")


def find_matching_paren(text: str, opening: int) -> int | None:
    depth = 0
    quote: str | None = None
    i = opening

    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return None


def split_columns(text: str) -> list[str]:
    result: list[str] = []
    start = 0
    parens = 0
    angles = 0
    quote: str | None = None
    i = 0

    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
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
            result.append(text[start:i])
            start = i + 1
        i += 1

    result.append(text[start:])
    return result


def validate_dataset(path: Path, sql: str, errors: list[str]) -> None:
    match = DATASET_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE SCHEMA IF NOT EXISTS")
        return

    name = match.group(1)
    if name != path.stem or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: dataset name must be uppercase and match {path.stem}")

    options = sql[match.end() :]
    if not re.search(r"\blocation\s*=\s*['\"]us-central1['\"]", options, re.I):
        errors.append(f"{path}: dataset location must be us-central1")
    if not re.search(r"\bdescription\s*=\s*['\"][^'\"]+['\"]", options, re.I):
        errors.append(f"{path}: dataset description is required")


def validate_table(path: Path, sql: str, errors: list[str]) -> None:
    match = TABLE_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE TABLE")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    if name != path.stem or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: table name must be uppercase and match {path.stem}")
    if len(parts) >= 2 and parts[-2] != path.parts[-3]:
        errors.append(f"{path}: SQL dataset must match its directory {path.parts[-3]}")
    if re.search(r"\bCREATE\s+OR\s+REPLACE\s+TABLE\b", match.group(0), re.I):
        errors.append(f"{path}: CREATE OR REPLACE TABLE can overwrite data; use a reviewed migration")

    opening = sql.find("(", match.end())
    closing = find_matching_paren(sql, opening) if opening >= 0 else None
    if closing is None:
        errors.append(f"{path}: could not parse table columns")
        return

    for column in split_columns(sql[opening + 1 : closing]):
        column = column.strip()
        column_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+", column)
        if not column_match:
            errors.append(f"{path}: could not parse column {column[:50]!r}")
            continue

        column_name = column_match.group(1)
        if not IDENTIFIER.fullmatch(column_name):
            errors.append(f"{path}: column {column_name} must be uppercase")
        if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", column, re.I | re.S):
            errors.append(f"{path}: column {column_name} requires a description")

    if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", sql[closing + 1 :], re.I | re.S):
        errors.append(f"{path}: table description is required")


def validate_view(path: Path, sql: str, errors: list[str]) -> None:
    match = VIEW_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE VIEW")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    folder_dataset = path.parts[-3]
    expected_dataset = f"{folder_dataset}_V"

    if len(parts) < 2 or parts[-2] != expected_dataset:
        errors.append(
            f"{path}: view SQL dataset must be {expected_dataset} "
            f"for the {folder_dataset} folder"
        )
    if (
        not name.endswith("_V")
        or name != path.stem
        or not IDENTIFIER.fullmatch(name)
    ):
        errors.append(
            f"{path}: view name must be uppercase, end in _V, "
            "and match the filename"
        )
    if not re.search(r"\bOPTIONS\s*\(.*?\bdescription\s*=", sql, re.I | re.S):
        errors.append(f"{path}: view description is required")


def validate_routine(path: Path, sql: str, errors: list[str]) -> None:
    match = PROCEDURE_RE.search(sql)
    if not match:
        errors.append(f"{path}: expected CREATE PROCEDURE")
        return

    parts = object_parts(match.group(1))
    name = parts[-1]
    dataset = path.parts[-3]

    if not name.startswith("SP_") or not IDENTIFIER.fullmatch(name):
        errors.append(f"{path}: procedure name must be uppercase and start with SP_")
    if name != path.stem:
        errors.append(f"{path}: procedure name must match filename {path.stem}")
    if len(parts) < 2 or parts[-2] != dataset:
        errors.append(f"{path}: procedure SQL dataset must match directory {dataset}")

    comments = re.findall(r"--[^\r\n]*|/\*.*?\*/", sql, re.S)
    for comment in comments:
        comment_text = re.sub(r"^(?:--|/\*|\*/|\*)", "", comment, flags=re.M).strip()
        if COMMENTED_SQL_RE.search(comment_text):
            errors.append(f"{path}: commented-out SQL code is not allowed")
            break


def changed_files(base: str, head: str) -> list[Path]:
    if re.fullmatch(r"0+", base):
        raise ValueError("The base commit is unavailable; merge a follow-up commit to run this validation.")

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base}...{head}",
            "--",
            "BigQuery",
            "DataProc",
            "dags",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / name for name in result.stdout.splitlines()]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_changed_assets.py BASE_SHA HEAD_SHA", file=sys.stderr)
        return 2

    try:
        files = changed_files(sys.argv[1], sys.argv[2])
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Could not determine changed files: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    validated = 0

    for path in files:
        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)
        if path.suffix == ".py":
            try:
                compile(path.read_text(encoding="utf-8"), str(relative), "exec")
            except (SyntaxError, UnicodeDecodeError) as exc:
                errors.append(f"{relative}: Python validation failed: {exc}")
            validated += 1
            continue

        if path.suffix != ".sql" or relative.parts[0] != "BigQuery":
            continue

        sql = normalize_sql(path.read_text(encoding="utf-8-sig"))
        parts = relative.parts

        if len(parts) == 3 and parts[1] == "DATASETS":
            validate_dataset(path, sql, errors)
        elif len(parts) == 4 and parts[2] == "TABLES":
            validate_table(path, sql, errors)
        elif len(parts) == 4 and parts[2] == "VIEWS":
            validate_view(path, sql, errors)
        elif len(parts) == 4 and parts[2] == "ROUTINES":
            validate_routine(path, sql, errors)
        else:
            errors.append(f"{relative}: SQL file is not in a recognized BigQuery asset directory")
        validated += 1

    if errors:
        print("Changed-file validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Changed-file validation passed ({validated} changed files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())