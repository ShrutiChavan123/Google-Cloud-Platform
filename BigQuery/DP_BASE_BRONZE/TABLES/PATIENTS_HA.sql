CREATE OR REPLACE EXTERNAL TABLE dp-dwh-dev.DP_BASE_BRONZE.PATIENTS_HA
(
  PATIENTID STRING OPTIONS(description="Unique identifier for the patient"),
  FIRSTNAME STRING OPTIONS(description="Patient's first name"),
  MIDDLENAME STRING OPTIONS(description="Patient's middle name"),
  LASTNAME STRING OPTIONS(description="Patient's last name"),
  DOB INT64 OPTIONS(description="Patient's date of birth"),
  GENDER STRING OPTIONS(description="Patient's gender"),
  SSN STRING OPTIONS(description="Patient's Social Security Number"),
  PHONENUMBER STRING OPTIONS(description="Patient's primary phone number"),
  ADDRESS STRING OPTIONS(description="Patient's residential address"),
  MODIFIEDDATE INT64 OPTIONS(description="Last record modification timestamp")
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://dp-dwh-dev-health-care-domain/landing/hospital-a/patients/*.json'],
  description = "Hospital A master patient index"
);