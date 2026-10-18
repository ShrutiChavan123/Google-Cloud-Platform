CREATE TABLE IF NOT EXISTS DP_BASE_SILVER.PATIENTS(
  PATIENT_KEY STRING
  OPTIONS (description = 'Surrogate key for the patient'), SRC_PATIENTID STRING
  OPTIONS (description = 'Original patient ID from the source system'),
  FIRSTNAME STRING
  OPTIONS (description = 'Legal first name of the patient'), LASTNAME STRING
  OPTIONS (description = 'Legal last name of the patient'), MIDDLENAME STRING
  OPTIONS (description = 'Legal middle name of the patient'), SSN STRING
  OPTIONS (description = 'Social Security Number'), PHONENUMBER STRING
  OPTIONS (description = 'Contact phone number'), GENDER STRING
  OPTIONS (description = 'Biological gender of the patient'), DOB INT64
  OPTIONS (description = 'Date of birth represented as a numeric value'),
  ADDRESS STRING
  OPTIONS (description = 'Residential address of the patient'),
  SRC_MODIFIEDDATE INT64
  OPTIONS (description = 'Last modified date in the source system'),
  DATASOURCE STRING
  OPTIONS (description = 'Identifier for the source system'),
  IS_QUARANTINED BOOL
  OPTIONS (
    description = 'Flag indicating if the record is quarantined for data quality issues'),
  INSERTED_DATE TIMESTAMP
  OPTIONS (
    description = 'Timestamp when the record was inserted into the silver layer'),
  MODIFIED_DATE TIMESTAMP
  OPTIONS (
    description = 'Timestamp when the record was last modified in the silver layer'),
  IS_CURRENT BOOL
  OPTIONS (
    description = 'Flag indicating if this is the current active record for the patient'))
  OPTIONS (
    description = 'Silver layer table containing unified and cleaned patient master data');