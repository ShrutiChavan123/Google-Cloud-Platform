CREATE OR REPLACE EXTERNAL TABLE dp-dwh-dev.DP_BASE_BRONZE.PROVIDERS_HA
(
  PROVIDERID STRING OPTIONS(description="Unique identifier for the provider"),
  FIRSTNAME STRING OPTIONS(description="Provider's first name"),
  LASTNAME STRING OPTIONS(description="Provider's last name"),
  SPECIALIZATION STRING OPTIONS(description="Medical area of expertise"),
  NPI INT64 OPTIONS(description="National Provider Identifier"),
  DEPTID STRING OPTIONS(description="Associated department ID")
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://dp-dwh-dev-health-care-domain/landing/hospital-a/providers/*.json'],
  description = "Hospital A healthcare provider directory"
);