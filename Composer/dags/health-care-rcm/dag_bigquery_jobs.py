from datetime import timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
)

PROJECT_ID = Variable.get("PROJECT_ID")
REGION = Variable.get("REGION")
SILVER_SP = Variable.get("SILVER_SP", deserialize_json=True)
GOLD_SP = Variable.get("GOLD_SP", deserialize_json=True)

default_args = {
    "owner": "Shruti Chavan",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="dag_bigquery_jobs",
    schedule=None,
    catchup=False,
    max_active_tasks=2,
    max_active_runs=1,
    default_args=default_args,
    tags=["gcs", "bq", "etl"],
) as dag:
    start = EmptyOperator(task_id="start_task")

    silver_tasks = []
    for procedure in SILVER_SP:
        task = BigQueryInsertJobOperator(
            task_id=f"silver_{procedure.lower()}",
            configuration={
                "query": {
                    "query": (
                        f"CALL `{PROJECT_ID}.DP_BASE_SILVER.{procedure}`();"
                    ),
                    "useLegacySql": False,
                }
            },
            location=REGION,
        )
        silver_tasks.append(task)

    silver_complete = EmptyOperator(task_id="silver_complete")

    gold_tasks = []
    for procedure in GOLD_SP:
        task = BigQueryInsertJobOperator(
            task_id=f"gold_{procedure.lower()}",
            configuration={
                "query": {
                    "query": (
                        f"CALL `{PROJECT_ID}.DP_BASE_GOLD.{procedure}`();"
                    ),
                    "useLegacySql": False,
                }
            },
            location=REGION,
        )
        gold_tasks.append(task)

    end = EmptyOperator(task_id="end_task")

    start >> silver_tasks
    for task in silver_tasks:
        task >> silver_complete

    silver_complete >> gold_tasks
    gold_tasks >> end