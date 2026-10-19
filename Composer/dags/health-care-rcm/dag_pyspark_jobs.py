from datetime import timedelta
import json
from airflow import DAG
from airflow.models import Variable
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocStartClusterOperator,
    DataprocStopClusterOperator,
    DataprocSubmitJobOperator,
)

# Airflow Variables
PROJECT_ID = Variable.get("PROJECT_ID")
REGION = Variable.get("REGION")
CLUSTER_NAME = Variable.get("CLUSTER_NAME")
COMPOSER_BUCKET = Variable.get("COMPOSER_BUCKET")

# JSON Variable
JOBS = Variable.get("PYSPARK_JOBS", deserialize_json=True)

default_args = {
    "owner": "Shruti Chavan",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="dag_pyspark_jobs",
    default_args=default_args,
    description="Start Dataproc cluster, execute PySpark jobs, stop cluster",
    schedule_interval=None,
    catchup=False,
    tags=["pyspark", "dataproc", "healthcare"],
) as dag:

    # Start Dataproc Cluster
    start_cluster = DataprocStartClusterOperator(
        task_id="start_cluster",
        project_id=PROJECT_ID,
        region=REGION,
        cluster_name=CLUSTER_NAME,
    )

    # Stop Dataproc Cluster
    stop_cluster = DataprocStopClusterOperator(
        task_id="stop_cluster",
        project_id=PROJECT_ID,
        region=REGION,
        cluster_name=CLUSTER_NAME,
        trigger_rule="all_done",  # Ensure cluster stops even if a job fails
    )

    previous_task = start_cluster

    for job_name in JOBS:

        current_task = DataprocSubmitJobOperator(
            task_id=job_name,
            project_id=PROJECT_ID,
            region=REGION,
            job={
                "placement": {
                    "cluster_name": CLUSTER_NAME
                },
                "pyspark_job": {
                    "main_python_file_uri": (
                        f"gs://{COMPOSER_BUCKET}/dags/dag_controls/{job_name}.py"
                    )
                },
            },
        )

        previous_task >> current_task
        previous_task = current_task

    previous_task >> stop_cluster
