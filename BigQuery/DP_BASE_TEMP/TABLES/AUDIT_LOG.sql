CREATE TABLE DP_BASE_TEMP.AUDIT_LOG(
 DATA_SOURCE STRING
 OPTIONS (description = 'The source system or origin of the data'),
 TABLENAME STRING
 OPTIONS (description = 'The name of the target table being loaded'),
 LOAD_TYPE STRING
 OPTIONS (
 description = 'The type of load operation (e.g., Full, Incremental)'),
 RECORD_COUNT INT64
 OPTIONS (description = 'The total number of records processed in the load'),
 LOAD_TIMESTAMP TIMESTAMP
 OPTIONS (description = 'The date and time when the load occurred'),
 STATUS STRING
 OPTIONS (
 description = 'The final status of the load operation (e.g., Success, Failed)'))
 OPTIONS (
 description = 'Table for auditing data loading processes and tracking record counts');