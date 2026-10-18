CREATE TABLE IF NOT EXISTS DP_BASE_SILVER.PROVIDERS(
  PROVIDERID STRING
  OPTIONS (description = 'Unique identifier for the healthcare provider'),
  FIRSTNAME STRING
  OPTIONS (description = 'Legal first name of the provider'), LASTNAME STRING
  OPTIONS (description = 'Legal last name of the provider'),
  SPECIALIZATION STRING
  OPTIONS (description = 'Medical specialty or area of expertise'),
  DEPTID STRING
  OPTIONS (description = 'Department identifier where the provider operates'),
  NPI INT64
  OPTIONS (description = 'National Provider Identifier'), DATASOURCE STRING
  OPTIONS (description = 'Original source system of the provider data'),
  IS_QUARANTINED BOOLEAN
  OPTIONS (
    description = 'Flag indicating if the record failed validation rules'))
  OPTIONS (
    description = 'Silver layer table containing unified and cleaned provider information');