CREATE TABLE IF NOT EXISTS DP_BASE_SILVER.ENCOUNTERS(
  ENCOUNTER_KEY STRING
  OPTIONS (
    description = 'Surrogate key for the encounter, typically a hash of source ID and system'),
  SRC_ENCOUNTERID STRING
  OPTIONS (
    description = 'Original encounter identifier from the source system'),
  PATIENTID STRING
  OPTIONS (
    description = 'Identifier for the patient associated with this encounter'),
  PROVIDERID STRING
  OPTIONS (
    description = 'Identifier for the provider associated with this encounter'),
  DEPARTMENTID STRING
  OPTIONS (
    description = 'Identifier for the department where the encounter occurred'),
  ENCOUNTERDATE INT64
  OPTIONS (
    description = 'Date of the encounter in numeric format (e.g., YYYYMMDD)'),
  ENCOUNTERTYPE STRING
  OPTIONS (
    description = 'Type of encounter (e.g., Inpatient, Outpatient, Emergency)'),
  PROCEDURECODE INT64
  OPTIONS (
    description = 'Medical procedure code associated with the encounter'),
  SRC_MODIFIEDDATE INT64
  OPTIONS (description = 'Last modified date in the source system'),
  DATASOURCE STRING
  OPTIONS (
    description = 'Identifier for the source system (e.g., Hospital A, Hospital B)'),
  IS_QUARANTINED BOOL
  OPTIONS (
    description = 'Flag indicating if the record failed data quality checks'),
  INSERTED_DATE TIMESTAMP
  OPTIONS (
    description = 'Timestamp when the record was loaded into the silver layer'),
  MODIFIED_DATE TIMESTAMP
  OPTIONS (
    description = 'Timestamp when the record was last modified in the silver layer'),
  IS_CURRENT BOOL
  OPTIONS (
    description = 'SCD Type 2 flag indicating if this is the active record version'))
  OPTIONS (
    description = 'Silver layer table containing unified and cleaned clinical encounters');