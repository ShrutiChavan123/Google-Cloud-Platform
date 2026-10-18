CREATE OR REPLACE EXTERNAL TABLE dp-dwh-dev.DP_BASE_BRONZE.ENCOUNTERS_HA
(
 ENCOUNTERID STRING OPTIONS(description="Unique identifier for the encounter"),
  PATIENTID STRING OPTIONS(description="Identifier for the patient"),
  PROVIDERID STRING OPTIONS(description="Identifier for the healthcare provider"),
  DEPARTMENTID STRING OPTIONS(description="Identifier for the department"),
  ENCOUNTERDATE INT64 OPTIONS(description="Timestamp of the encounter"),
  ENCOUNTERTYPE STRING OPTIONS(description="Type of medical encounter"),
  PROCEDURECODE INT64 OPTIONS(description="Code for the medical procedure performed"),
  MODIFIEDDATE INT64 OPTIONS(description="Timestamp when the record was last modified"),
  INSERTEDDATE INT64 OPTIONS(description="Timestamp when the record was inserted")
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://dp-dwh-dev-health-care-domain/landing/hospital-a/encounters/*.json'],
  description = "Hospital A patient encounter records"
);
