from pyspark.sql import SparkSession, functions as f

# Create Spark session
spark = SparkSession.builder \
                    .appName("Healthcare Claims Ingestion") \
                    .getOrCreate()

# configure variables
BUCKET_NAME = "dp-dwh-dev-health-care-domain"
CLAIMS_BUCKET_PATH = f"gs://{BUCKET_NAME}/landing/claims/*.csv"
BQ_TABLE = "dp-dwh-dev.DP_BASE_BRONZE.CLAIMS"
TEMP_GCS_BUCKET = f"{BUCKET_NAME}/temp/"

# read from claims source
claims_df = spark.read.csv(CLAIMS_BUCKET_PATH, header=True)

# adding hospital source for future reference
claims_df = (claims_df
                .withColumn("DATASOURCE", 
                              f.when(f.input_file_name().contains("hospital2"), "hosp-b")
                               .when(f.input_file_name().contains("hospital1"), "hosp-a").otherwise("None")))

# TRANSFORM COLUMNS TO UPPERCASE
# This line grabs all existing columns and applies .upper() to them
claims_df = claims_df.toDF(*[c.upper() for c in claims_df.columns])

# dropping duplicates if any
claims_df = claims_df.dropDuplicates()

# write to bigquery
(claims_df.write
            .format("bigquery")
            .option("table", BQ_TABLE)
            .option("temporaryGcsBucket", TEMP_GCS_BUCKET)
            .mode("overwrite")
            .save())
