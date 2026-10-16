# Google Cloud Healthcare Data Platform

This project demonstrates an end-to-end healthcare analytics solution built on the Google Cloud Platform (GCP). It is designed to ingest, process, store, and analyze healthcare data from multiple hospital sources and support reporting on patient, provider, encounter, and financial metrics.

The repository includes source SQL schema definitions, healthcare data files, and BigQuery dataset setup scripts to model a modern healthcare data platform.

## Project Overview

The objective of this project is to build a scalable healthcare data pipeline that can:
- Ingest patient, provider, encounter, claims, and transaction data from multiple hospital systems
- Store raw and structured data in secure cloud services
- Transform and standardize data for reporting and analysis
- Enable analytics on utilization, revenue, provider performance, and claim trends
- Support a healthcare decision-support and reporting layer on Google Cloud

This solution is aligned with typical healthcare data engineering patterns used in hospital analytics, claims processing, and operational reporting.

## Business Use Cases

This platform can support several key healthcare scenarios:
- Patient and encounter analytics
- Claim and payment trend analysis
- Department and provider performance reports
- Procedure and CPT utilization tracking
- Revenue cycle monitoring
- Data quality and standardized healthcare reporting

## GCP Tech Stack

The project uses a modern GCP-based architecture for healthcare data processing and analytics:

- Google Cloud Storage (GCS): Raw data landing zone for CSV and source files
- Cloud SQL: Structured storage for hospital source tables and operational data
- BigQuery: Enterprise data warehouse for analytics and reporting
- Dataflow / Apache Beam: ETL and transformation pipeline processing
- IAM & Security: Access control, least privilege, and governance
- GitHub: Version control and project collaboration

## Architecture

The typical architecture for this project is as follows:

1. Healthcare source files are stored in the `Data/` folder:
   - `claims/`
   - `cptcodes/`
   - `hospital-a/`
   - `hospital-b/`
   - `configs/`

2. Raw datasets are loaded into Google Cloud Storage for staging or ingestion.

3. Operational and source system data is modeled using Cloud SQL DDL scripts:
   - `Cloudsql/Hospital-a/tables.sql`
   - `Cloudsql/Hospital-b/tables.sql`

4. Healthcare facts and dimensions are transformed into analytical tables in BigQuery.

5. The analytical dataset is created via:
   - `BigQuery/DATASETS/DP_BASE_TEMP.sql`

6. Reporting and dashboards visualize KPIs such as:
   - Patient count
   - Encounter volume
   - Provider specialties
   - Claim amount and paid amount
   - Department-level metrics
   - Procedure code usage

## Data Model

The project includes healthcare tables such as:
- `departments`
- `patients`
- `providers`
- `encounters`
- `transactions`
- `claims`
- `cptcodes`

These tables represent common healthcare operational dimensions and facts:
- Patient demographics
- Hospital departments
- Provider information
- Clinical encounters
- Procedure codes
- Financial claims and payment activity

## Repository Structure

```text
Google-Cloud-Platform/
├── README.md
├── BigQuery/
│   └── DATASETS/
│       └── DP_BASE_TEMP.sql
├── Cloudsql/
│   ├── Hospital-a/
│   │   └── tables.sql
│   └── Hospital-b/
│       └── tables.sql
└── Data/
    ├── claims/
    ├── configs/
    ├── cptcodes/
    ├── hospital-a/
    └── hospital-b/