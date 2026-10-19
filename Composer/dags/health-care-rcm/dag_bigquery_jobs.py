from airflow import DAG
from datetime import timedelta
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.models import Variable

# Airflow Variables
PROJECT_ID = Variable.get("PROJECT_ID")
REGION = Variable.get("REGION")
SILVER_SP = Variable.get("SILVER_SP", deserialize_json=True)
GOLD_SP = Variable.get("GOLD_SP", deserialize_json=True)

args = {
    "owner": "Shruti Chavan",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="dag_bigquery_jobs",
    schedule_interval=None,
    catchup=False,
    default_args=args,
    tags=["gcs", "bq", "etl"],
) as dag:

    start = EmptyOperator(task_id="start_task")
	
	#Data transfornation and load to silver tables
    silver_table_load = []

    for sp in SILVER_SP:
        task = BigQueryInsertJobOperator(
            task_id=f"call_{sp.lower()}",
            configuration={
                "query": {
                    "query": f"""
                    CALL `{PROJECT_ID}.DP_BASE_SILVER.{sp}`();
                    """,
                    "useLegacySql": False,
                }
            },
            location=REGION,
        )
        silver_table_load.append(task)

	#Data load to gold tables for businessusers
    gold_table_load = []

    for sp in GOLD_SP:
        task = BigQueryInsertJobOperator(
            task_id=f"call_{sp.lower()}",
            configuration={
                "query": {
                    "query": f"""
                    CALL `{PROJECT_ID}.DP_BASE_GOLD.{sp}`();
                    """,
                    "useLegacySql": False,
                }
            },
            location=REGION,
        )
        gold_table_load.append(task)
		
		
    silver_complete = EmptyOperator(
    task_id="silver_complete"
    )
    
    end = EmptyOperator(task_id="end_task")

    start >> silver_table_load
    
    for task in silver_table_load:
        task >> silver_complete
    
    silver_complete >> gold_table_load
    
    gold_table_load >> end