CREATE TABLE IF NOT EXISTS DP_BASE_SILVER.TRANSACTIONS(
  TRANSACTION_KEY STRING
  OPTIONS (
    description = 'Surrogate key for the transaction, typically a hash of source ID and system'),
  SRC_TRANSACTIONID STRING
  OPTIONS (
    description = 'Original transaction identifier from the source system'),
  ENCOUNTERID STRING
  OPTIONS (
    description = 'Identifier for the clinical encounter associated with this transaction'),
  PATIENTID STRING
  OPTIONS (
    description = 'Identifier for the patient associated with this transaction'),
  PROVIDERID STRING
  OPTIONS (
    description = 'Identifier for the provider associated with this transaction'),
  DEPTID STRING
  OPTIONS (
    description = 'Identifier for the department where the service was rendered'),
  VISITDATE INT64
  OPTIONS (
    description = 'Date of the patient visit in numeric format (e.g., YYYYMMDD)'),
  SERVICEDATE INT64
  OPTIONS (description = 'Date the service was performed in numeric format'),
  PAIDDATE INT64
  OPTIONS (description = 'Date the transaction was paid in numeric format'),
  VISITTYPE STRING
  OPTIONS (
    description = 'Type of visit (e.g., Inpatient, Outpatient, Emergency)'),
  AMOUNT FLOAT64
  OPTIONS (description = 'Transaction amount'), AMOUNTTYPE STRING
  OPTIONS (description = 'Type of amount (e.g., Charged, Adjustment, Payment)'),
  PAIDAMOUNT FLOAT64
  OPTIONS (description = 'Actual amount paid for this transaction'),
  CLAIMID STRING
  OPTIONS (
    description = 'Identifier for the insurance claim associated with this transaction'),
  PAYORID STRING
  OPTIONS (description = 'Identifier for the insurance payor'),
  PROCEDURECODE INT64
  OPTIONS (description = 'Medical procedure code (e.g., CPT/HCPCS)'),
  ICDCODE STRING
  OPTIONS (description = 'Diagnosis code (ICD-9 or ICD-10)'),
  LINEOFBUSINESS STRING
  OPTIONS (description = 'Line of business associated with the transaction'),
  MEDICAIDID STRING
  OPTIONS (description = 'Medicaid identifier if applicable'), MEDICAREID STRING
  OPTIONS (description = 'Medicare identifier if applicable'),
  SRC_INSERTDATE INT64
  OPTIONS (description = 'Insertion date in the source system'),
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
    description = 'Silver layer table containing unified and cleaned financial transactions');