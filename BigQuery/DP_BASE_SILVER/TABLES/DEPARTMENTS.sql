CREATE TABLE IF NOT EXISTS  dp-dwh-dev.DP_BASE_SILVER.DEPARTMENTS
(
  DEPARTMENT_ID STRING OPTIONS(description="The unique identifier for the department as defined in the master system."),
  SRC_ID STRING OPTIONS(description="The original identifier of the department record from the source system."),
  NAME STRING OPTIONS(description="The full descriptive name of the department."),
  DATASOURCE STRING OPTIONS(description="The specific source system the data originated from (e.g., hosp-a, hosp-b)."),
  IS_QUARANTINE BOOLEAN OPTIONS(description="Flag indicating if the record failed initial validation rules and is held for review.")
)
OPTIONS (
  description = "Silver layer dimension table for Departments. Contains cleaned, validated, and consolidated data from all hospital sources.",
  labels = [("layer", "silver"), ("subject_area", "healthcare")]
);