CREATE OR REPLACE EXTERNAL TABLE dp-dwh-dev.DP_BASE_BRONZE.TRANSACTIONS_HB
(
  TRANSACTIONID STRING OPTIONS(description="Unique identifier for the transaction"),
  PATIENTID STRING OPTIONS(description="Associated patient ID"),
  ENCOUNTERID STRING OPTIONS(description="Associated encounter ID"),
  PROVIDERID STRING OPTIONS(description="Associated provider ID"),
  DEPTID STRING OPTIONS(description="Associated department ID"),
  VISITDATE INT64 OPTIONS(description="Date of the visit"),
  SERVICEDATE INT64 OPTIONS(description="Date service was rendered"),
  PAIDDATE INT64 OPTIONS(description="Date payment was processed"),
  VISITTYPE STRING OPTIONS(description="Type of visit for billing"),
  AMOUNT FLOAT64 OPTIONS(description="Total transaction amount"),
  PAIDAMOUNT FLOAT64 OPTIONS(description="Total amount paid"),
  AMOUNTTYPE STRING OPTIONS(description="Category of the amount"),
  CLAIMID STRING OPTIONS(description="Insurance claim identifier"),
  PAYORID STRING OPTIONS(description="Insurance payor identifier"),
  PROCEDURECODE INT64 OPTIONS(description="Procedure code billed"),
  ICDCODE STRING OPTIONS(description="Diagnosis code (ICD)"),
  LINEOFBUSINESS STRING OPTIONS(description="Healthcare line of business"),
  MEDICAREID STRING OPTIONS(description="Medicare identifier"),
  MEDICAIDID STRING OPTIONS(description="Medicaid identifier"),
  INSERTDATE INT64 OPTIONS(description="Record creation timestamp"),
  MODIFIEDDATE INT64 OPTIONS(description="Record update timestamp")
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://dp-dwh-dev-health-care-domain/landing/hospital-b/transactions/*.json'],
  description = "Hospital B financial transaction records"
);