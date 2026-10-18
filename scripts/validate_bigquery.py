from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parents[1]
ASSET_ORDER = ("DATASETS", "TABLES", "VIEWS", "ROUTINES", "MIGRATIONS")


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", flush=True)


def get_changed_sql(base_sha: str, head_sha: str) -> list[Path]:
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

    paths = [ROOT / name for name in result.stdout.splitlines() if name.endswith(".sql")]

    def category_order(path: Path) -> int:
        try:
            return ASSET_ORDER.index(path.relative_to(ROOT).parts[2])
        except (ValueError, IndexError):
            return len(ASSET_ORDER)

    return sorted(paths, key=category_order)


def main() -> int:
    if len(sys.argv) != 3:
        log("ERROR: Usage: deploy_bigquery.py BASE_SHA HEAD_SHA")
        return 2

    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        log("ERROR: GCP_PROJECT_ID is not set.")
        return 1

    try:
        sql_files = get_changed_sql(sys.argv[1], sys.argv[2])
    except subprocess.CalledProcessError as exc:
        log(f"ERROR: Could not determine changed SQL files: {exc.stderr.strip()}")
        return 1

    if not sql_files:
        log("No changed BigQuery SQL files to deploy.")
        return 0

    client = bigquery.Client(project=project_id)
    log(f"Starting deployment of {len(sql_files)} changed SQL file(s) to {project_id}.")

    for path in sql_files:
        relative_path = path.relative_to(ROOT)
        log(f"Deploying {relative_path} ...")

        try:
            sql = path.read_text(encoding="utf-8-sig")
            job = client.query(sql, location="us-central1")
            job.result()

            log(f"SUCCESS: {relative_path}")
            log(f"  BigQuery job ID: {job.job_id}")
            log(f"  Statement type: {job.statement_type or 'unknown'}")

            if job.num_dml_affected_rows is not None:
                log(f"  Rows modified: {job.num_dml_affected_rows}")

            if job.ddl_operation_performed:
                log(f"  DDL operation: {job.ddl_operation_performed}")
                if job.ddl_target_table:
                    log(f"  DDL target table: {job.ddl_target_table}")
                if job.ddl_target_routine:
                    log(f"  DDL target routine: {job.ddl_target_routine}")

            if job.total_bytes_processed is not None:
                log(f"  Bytes processed: {job.total_bytes_processed}")

        except (OSError, UnicodeError, GoogleAPICallError) as exc:
            log(f"FAILED: {relative_path}")
            log(f"  Error: {exc}")
            return 1

    log(f"Deployment completed successfully ({len(sql_files)} SQL file(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())