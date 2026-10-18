from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_OBJECT = r"(?:`[^`]+`|[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){0,2})"

BACKUP_RE = re.compile(
    rf"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:SNAPSHOT\s+)?TABLE\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?(?P<backup>{SQL_OBJECT})\s+"
    rf"(?:CLONE\s+(?P<clone>{SQL_OBJECT})|"
    rf"AS\s+SELECT\b.*?\bFROM\s+(?P<source>{SQL_OBJECT}))",
    re.IGNORECASE | re.DOTALL,
)

MUTATION_RE = re.compile(
    rf"^\s*(?P<operation>"
    rf"CREATE\s+OR\s+REPLACE\s+TABLE|"
    rf"ALTER\s+TABLE|"
    rf"TRUNCATE\s+TABLE|"
    rf"DELETE\s+FROM|"
    rf"INSERT(?:\s+INTO)?|"
    rf"UPDATE|"
    rf"MERGE\s+INTO"
    rf")\s+(?P<target>{SQL_OBJECT})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PlannedStatement:
    date_folder: str
    file_name: str
    index: int
    sql: str
    phase: int
    target: str | None
    backup_source: str | None


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", flush=True)


def canonical_name(name: str) -> str:
    return name.strip("`").upper()


def strip_sql_comments(sql: str) -> str:
    result: list[str] = []
    quote: str | None = None
    i = 0

    while i < len(sql):
        char = sql[i]

        if quote:
            result.append(char)
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    result.append(sql[i + 1])
                    i += 1
                else:
                    quote = None
            elif char == "\\" and i + 1 < len(sql):
                result.append(sql[i + 1])
                i += 1
        elif char in ("'", '"', "`"):
            quote = char
            result.append(char)
        elif sql.startswith("--", i):
            while i < len(sql) and sql[i] not in "\r\n":
                i += 1
            result.append(" ")
            continue
        elif sql.startswith("/*", i):
            i += 2
            while i < len(sql) and not sql.startswith("*/", i):
                if sql[i] in "\r\n":
                    result.append(sql[i])
                i += 1
            if i == len(sql):
                raise ValueError("Unterminated SQL block comment")
            i += 2
            result.append(" ")
            continue
        else:
            result.append(char)

        i += 1

    return "".join(result)


def split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    start = 0
    quote: str | None = None
    i = 0

    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1
                else:
                    quote = None
            elif char == "\\":
                i += 1
        elif char in ("'", '"', "`"):
            quote = char
        elif char == ";":
            statement = sql[start:i].strip()
            if statement:
                statements.append(statement)
            start = i + 1
        i += 1

    trailing = sql[start:].strip()
    if trailing:
        statements.append(trailing)

    return statements


def phase_for(operation: str) -> int:
    normalized = " ".join(operation.upper().split())

    if normalized in {"CREATE OR REPLACE TABLE", "ALTER TABLE"}:
        return 1
    if normalized in {"TRUNCATE TABLE", "DELETE FROM"}:
        return 2
    if normalized.startswith("INSERT"):
        return 3
    if normalized in {"UPDATE", "MERGE INTO"}:
        return 4

    raise ValueError(f"Unsupported DML operation: {operation}")


def dml_files_for_changes(base_sha: str, head_sha: str) -> list[Path]:
    if re.fullmatch(r"0+", base_sha):
        raise ValueError("Base commit is unavailable; cannot calculate changed DML files.")

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base_sha}...{head_sha}",
            "--",
            "BigQuery/DML",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return [
        ROOT / name
        for name in result.stdout.splitlines()
        if name.lower().endswith(".sql")
    ]


def build_plan(files: list[Path]) -> list[PlannedStatement]:
    plan: list[PlannedStatement] = []
    errors: list[str] = []

    for path in files:
        relative = path.relative_to(ROOT)
        parts = relative.parts

        if len(parts) != 4 or parts[:2] != ("BigQuery", "DML"):
            errors.append(
                f"{relative}: expected BigQuery/DML/MMDDYYYY/<file>.sql"
            )
            continue

        date_folder = parts[2]
        try:
            if not re.fullmatch(r"\d{8}", date_folder):
                raise ValueError
            datetime.strptime(date_folder, "%m%d%Y")
        except ValueError:
            errors.append(
                f"{relative}: date folder must be a valid MMDDYYYY date"
            )
            continue

        try:
            text = path.read_text(encoding="utf-8-sig")
            statements = split_statements(strip_sql_comments(text))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{relative}: could not read SQL: {exc}")
            continue

        if not statements:
            errors.append(f"{relative}: SQL file is empty")
            continue

        for index, statement in enumerate(statements, start=1):
            backup_match = BACKUP_RE.match(statement)
            if backup_match:
                backup_name = canonical_name(backup_match.group("backup"))
                source_name = canonical_name(
                    backup_match.group("clone") or backup_match.group("source")
                )
                backup_parts = backup_name.split(".")
                backup_table = backup_parts[-1]

                if (
                    len(backup_parts) < 2
                    or backup_parts[-2] != "DP_BASE_BACKUP"
                ):
                    errors.append(
                        f"{relative}, statement {index}: backup destination "
                        "must be in DP_BASE_BACKUP"
                    )
                    continue

                if not re.fullmatch(
                    r"[A-Z][A-Z0-9_]*_BKP_[A-Z0-9_-]+",
                    backup_table,
                ):
                    errors.append(
                        f"{relative}, statement {index}: backup table must be "
                        "DP_BASE_BACKUP.<TABLE_NAME>_BKP_<DATE>"
                    )
                    continue

                plan.append(
                    PlannedStatement(
                        date_folder=date_folder,
                        file_name=relative.as_posix(),
                        index=index,
                        sql=statement,
                        phase=0,
                        target=None,
                        backup_source=source_name,
                    )
                )
                continue

            mutation_match = MUTATION_RE.match(statement)
            if not mutation_match:
                errors.append(
                    f"{relative}, statement {index}: unsupported SQL; expected "
                    "a backup, CREATE OR REPLACE TABLE, ALTER TABLE, "
                    "TRUNCATE TABLE, DELETE FROM, INSERT, UPDATE, or MERGE"
                )
                continue

            operation = " ".join(
                mutation_match.group("operation").upper().split()
            )
            target = canonical_name(mutation_match.group("target"))

            try:
                phase = phase_for(operation)
            except ValueError as exc:
                errors.append(f"{relative}, statement {index}: {exc}")
                continue

            plan.append(
                PlannedStatement(
                    date_folder=date_folder,
                    file_name=relative.as_posix(),
                    index=index,
                    sql=statement,
                    phase=phase,
                    target=target,
                    backup_source=None,
                )
            )

    if errors:
        raise ValueError("\n".join(errors))

    plan.sort(
        key=lambda item: (
            datetime.strptime(item.date_folder, "%m%d%Y"),
            item.phase,
            item.file_name,
            item.index,
        )
    )

    backups_by_date: dict[str, set[str]] = {}
    for item in plan:
        if item.backup_source:
            backups_by_date.setdefault(item.date_folder, set()).add(
                item.backup_source
            )

    for item in plan:
        if item.target is None:
            continue
        if item.target not in backups_by_date.get(item.date_folder, set()):
            errors.append(
                f"{item.file_name}, statement {item.index}: {item.target} "
                f"has no matching changed backup in "
                f"BigQuery/DML/{item.date_folder}"
            )

    if errors:
        raise ValueError("\n".join(errors))

    return plan


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in {"validate", "deploy"}:
        log("ERROR: Usage: dml_batch.py validate|deploy BASE_SHA HEAD_SHA")
        return 2

    mode, base_sha, head_sha = sys.argv[1:4]

    try:
        files = dml_files_for_changes(base_sha, head_sha)
        plan = build_plan(files)
    except (subprocess.CalledProcessError, ValueError) as exc:
        log(f"ERROR: DML batch validation failed:\n{exc}")
        return 1

    if not plan:
        log("No changed DML statements to process.")
        return 0

    log(f"DML plan valid: {len(plan)} changed statement(s).")
    for position, item in enumerate(plan, start=1):
        kind = "BACKUP" if item.phase == 0 else "MUTATION"
        log(
            f"  {position}. {kind} | {item.file_name} "
            f"| statement {item.index}"
        )

    if mode == "validate":
        log("DML validation passed; deployment order is valid.")
        return 0

    try:
        from google.api_core.exceptions import GoogleAPICallError
        from google.cloud import bigquery
    except ImportError as exc:
        log(f"ERROR: BigQuery client is unavailable: {exc}")
        return 1

    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        log("ERROR: GCP_PROJECT_ID is not set.")
        return 1

    client = bigquery.Client(project=project_id)

    for position, item in enumerate(plan, start=1):
        log(
            f"Executing {position}/{len(plan)}: {item.file_name}, "
            f"statement {item.index}"
        )
        try:
            job = client.query(item.sql, location="us-central1")
            job.result()
            log(f"  SUCCESS. BigQuery job ID: {job.job_id}")
            log(f"  Statement type: {job.statement_type or 'unknown'}")
            if job.num_dml_affected_rows is not None:
                log(f"  Rows modified: {job.num_dml_affected_rows}")
            if job.ddl_operation_performed:
                log(f"  DDL operation: {job.ddl_operation_performed}")
                if job.ddl_target_table:
                    log(f"  Target table: {job.ddl_target_table}")
        except (GoogleAPICallError, ValueError) as exc:
            log(f"  FAILED: {exc}")
            return 1

    log(f"DML deployment completed ({len(plan)} statement(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())