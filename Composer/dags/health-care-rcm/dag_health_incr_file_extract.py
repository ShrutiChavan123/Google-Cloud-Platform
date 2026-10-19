import airflow
from airflow import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator


# Define default arguments
args = {
    "owner": "Shruti Chavan",
    "start_date": days_ago(1),
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "email_on_success": False
}

# Define the parent DAG
with DAG(
    dag_id="dag_health_incr_file_extract",
    schedule_interval="0 5 * * *",
    description="Parent DAG to trigger PySpark and BigQuery DAGs",
    default_args=args,
    tags=["parent", "orchestration", "etl"]
) as dag:

    start = EmptyOperator(task_id="start_task")

    # Task to trigger PySpark DAG
    dag_pyspark_jobs = TriggerDagRunOperator(
        task_id="dag_pyspark_jobs",
        trigger_dag_id="dag_pyspark_jobs",
        wait_for_completion=True,
    )

    # Task to trigger BigQuery DAG
    dag_bigquery_jobs = TriggerDagRunOperator(
        task_id="dag_bigquery_jobs",
        trigger_dag_id="dag_bigquery_jobs",
        wait_for_completion=True,
    )
    
    end = EmptyOperator(task_id="end_task")
    

# Define dependencies
start >> dag_pyspark_jobs >> dag_bigquery_jobs >> end