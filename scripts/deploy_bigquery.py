from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parents[1]


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", flush=True)


def asset_order(file_name: str) -> tuple[int, str]:
    parts = Path(file_name).parts

    if len(parts) == 3 and parts[:2] == ("BigQuery", "DATASETS"):
        return (0, file_name)
    if len(parts) == 4 and parts[2] == "TABLES":
        return (1, file_name)
    if len(parts) == 4 and parts[2] == "VIEWS":
        return (2, file_name)
    if len(parts) == 4 and parts[2] == "ROUTINES":
        return (3, file_name)
    if len(parts) == 4 and parts[1] == "DML":
        return (4, file_name)

    raise ValueError(f"Unrecognized BigQuery SQL asset path: {file_name}")


def changed_sql_files(base_sha: str, head_sha: str) -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base_sha}...{head_sha}",
            "--",
            "BigQuery",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    names = [
        name
        for name in result.stdout.splitlines()
        if name.lower().endswith(".sql")
        and not (
            len(Path(name).parts) == 4
            and Path(name).parts[1] == "DML"
        )
    ]

    for name in names:
        asset_order(name)

    return [ROOT / name for name in sorted(names, key=asset_order)]


def report_job(job: bigquery.QueryJob, label: str) -> None:
    job.result()

    log(f"{label}: completed successfully")
    log(f"  Job ID: {job.job_id}")
    log(f"  Statement type: {job.statement_type or 'unknown'}")

    if job.num_dml_affected_rows is not None:
        log(f"  Rows modified: {job.num_dml_affected_rows}")

    if job.ddl_operation_performed:
        log(f"  DDL operation: {job.ddl_operation_performed}")
        if job.ddl_target_table:
            log(f"  DDL target table: {job.ddl_target_table}")
        if job.ddl_target_routine:
            log(f"  DDL target routine: {job.ddl_target_routine}")


def report_script_child_jobs(
    client: bigquery.Client,
    parent_job: bigquery.QueryJob,
) -> None:
    child_jobs = list(
        client.list_jobs(
            project=client.project,
            parent_job=parent_job.job_id,
        )
    )
    child_jobs.sort(key=lambda child: (child.created or datetime.min.replace(tzinfo=timezone.utc)))

    if not child_jobs:
        log("  BigQuery reported no child statements for this script.")
        return

    for index, child in enumerate(child_jobs, start=1):
        report_job(child, f"  Statement {index}")


def main() -> int:
    if len(sys.argv) != 3:
        log("ERROR: Usage: deploy_bigquery.py BASE_SHA HEAD_SHA")
        return 2

    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        log("ERROR: GCP_PROJECT_ID is not set.")
        return 1

    base_sha, head_sha = sys.argv[1:3]

    try:
        files = changed_sql_files(base_sha, head_sha)
    except (subprocess.CalledProcessError, ValueError) as exc:
        detail = getattr(exc, "stderr", "")
        log(f"ERROR: Could not determine deployable SQL files: {detail or exc}")
        return 1

    if not files:
        log("No changed BigQuery SQL files to deploy.")
        return 0

    client = bigquery.Client(project=project_id)
    log(f"Deploying {len(files)} changed SQL file(s) to project {project_id}.")

    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        log(f"Starting: {relative_path}")

        try:
            sql = path.read_text(encoding="utf-8-sig")
            if not sql.strip():
                log(f"ERROR: {relative_path} is empty; refusing to deploy.")
                return 1

            job = client.query(sql, location="us-central1")
            job.result()

            if job.statement_type == "SCRIPT":
                log(f"SUCCESS: {relative_path} (BigQuery script)")
                log(f"  Parent job ID: {job.job_id}")
                report_script_child_jobs(client, job)
            else:
                report_job(job, f"SUCCESS: {relative_path}")

        except (OSError, UnicodeError, GoogleAPICallError) as exc:
            log(f"FAILED: {relative_path}")
            log(f"  Error: {exc}")
            return 1

    log(f"Deployment completed successfully ({len(files)} SQL file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())