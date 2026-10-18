CREATE OR REPLACE EXTERNAL TABLE dp-dwh-dev.DP_BASE_BRONZE.DEPARTMENTS_HB
(
  NAME STRING OPTIONS(description="The name of the department"),
  DEPTID STRING OPTIONS(description="Unique identifier for the department")
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://dp-dwh-dev-health-care-domain/landing/hospital-b/departments/*.json'],
  description = "Hospital B department reference data"
);