CREATE OR REPLACE PROCEDURE `dp-dwh-dev.DP_BASE_SILVER.SP_PATIENTS_SCD2`()
BEGIN
-- 1. Create a stage table from Bronze srcs with Uppercase Columns and Quality Logic
CREATE OR REPLACE TABLE `dp-dwh-dev.DP_BASE_TEMP.TEMP_PATIENTS`
AS
SELECT DISTINCT
  CONCAT(SRC_PATIENTID, '-', DATASOURCE) AS PATIENT_KEY,
  SRC_PATIENTID,
  FIRSTNAME,
  LASTNAME,
  MIDDLENAME,
  SSN,
  PHONENUMBER,
  GENDER,
  DOB,
  ADDRESS,
  MODIFIEDDATE AS SRC_MODIFIEDDATE,
  DATASOURCE,
  CASE
    WHEN
      SRC_PATIENTID IS NULL
      OR DOB IS NULL
      OR FIRSTNAME IS NULL
      OR LOWER(FIRSTNAME) = 'null'
      THEN TRUE
    ELSE FALSE
    END
    AS IS_QUARANTINED
FROM
  (
    -- src A: Hospital A
    SELECT DISTINCT
      PatientID AS SRC_PATIENTID,
      FirstName AS FIRSTNAME,
      LastName AS LASTNAME,
      MiddleName AS MIDDLENAME,
      SSN,
      PhoneNumber AS PHONENUMBER,
      Gender AS GENDER,
      DOB,
      Address AS ADDRESS,
      ModifiedDate AS MODIFIEDDATE,
      'hosa' AS DATASOURCE
    FROM `dp-dwh-dev.DP_BASE_BRONZE.PATIENTS_HA`
    UNION ALL

    -- src B: Hospital B (Mapping corrected based on actual schema)
    SELECT DISTINCT
      ID AS SRC_PATIENTID,
      F_NAME,
      L_NAME,
      M_NAME,
      SSN,
      PHONENUMBER, 
      GENDER,
      DOB,
      ADDRESS,
      MODIFIEDDATE,
      'hosb' AS DATASOURCE
    FROM `dp-dwh-dev.DP_BASE_BRONZE.PATIENTS_HB`
  );

-- 2. SCD Type 2 Part A: Expire (deactivate) existing records in Silver that have changed
MERGE INTO `DP_BASE_SILVER.PATIENTS` AS tgt
USING `dp-dwh-dev.DP_BASE_TEMP.TEMP_PATIENTS` AS src
ON
  tgt.PATIENT_KEY = src.PATIENT_KEY
  AND tgt.IS_CURRENT
    = TRUE
      WHEN
        MATCHED
        AND (
          tgt.SRC_PATIENTID <> src.SRC_PATIENTID
          OR tgt.FIRSTNAME <> src.FIRSTNAME
          OR tgt.LASTNAME <> src.LASTNAME
          OR tgt.MIDDLENAME <> src.MIDDLENAME
          OR tgt.SSN <> src.SSN
          OR tgt.PHONENUMBER <> src.PHONENUMBER
          OR tgt.GENDER <> src.GENDER
          OR tgt.DOB <> src.DOB
          OR tgt.ADDRESS <> src.ADDRESS
          OR tgt.SRC_MODIFIEDDATE <> src.SRC_MODIFIEDDATE
          OR tgt.DATASOURCE <> src.DATASOURCE
          OR tgt.IS_QUARANTINED <> src.IS_QUARANTINED)
        THEN UPDATE
SET tgt.IS_CURRENT = FALSE, tgt.MODIFIED_DATE = CURRENT_TIMESTAMP();

-- 3. SCD Type 2 Part B: Insert new records and the new versions of updated records
INSERT INTO `DP_BASE_SILVER.PATIENTS`
  (
    PATIENT_KEY,
    SRC_PATIENTID,
    FIRSTNAME,
    LASTNAME,
    MIDDLENAME,
    SSN,
    PHONENUMBER,
    GENDER,
    DOB,
    ADDRESS,
    SRC_MODIFIEDDATE,
    DATASOURCE,
    IS_QUARANTINED,
    INSERTED_DATE,
    MODIFIED_DATE,
    IS_CURRENT)
SELECT
  src.PATIENT_KEY,
  src.SRC_PATIENTID,
  src.FIRSTNAME,
  src.LASTNAME,
  src.MIDDLENAME,
  src.SSN,
  src.PHONENUMBER,
  src.GENDER,
  src.DOB,
  src.ADDRESS,
  src.SRC_MODIFIEDDATE,
  src.DATASOURCE,
  src.IS_QUARANTINED,
  CURRENT_TIMESTAMP(),
  CURRENT_TIMESTAMP(),
  TRUE
FROM `dp-dwh-dev.DP_BASE_TEMP.TEMP_PATIENTS` AS src
WHERE
  NOT EXISTS(
    SELECT 1
    FROM `DP_BASE_SILVER.PATIENTS` AS tgt
    WHERE tgt.PATIENT_KEY = src.PATIENT_KEY AND tgt.IS_CURRENT = TRUE
  );

-- 4. Cleanup the temporary staging table
DROP TABLE IF EXISTS `dp-dwh-dev.DP_BASE_TEMP.TEMP_PATIENTS`;

END;