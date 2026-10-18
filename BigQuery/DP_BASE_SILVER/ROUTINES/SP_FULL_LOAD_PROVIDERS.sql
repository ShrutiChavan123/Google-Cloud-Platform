CREATE OR REPLACE PROCEDURE `dp-dwh-dev.DP_BASE_SILVER.SP_FULL_LOAD_PROVIDERS`()
BEGIN
--full load table
-- 2. Truncate Silver Table Before Inserting 
TRUNCATE TABLE `DP_BASE_SILVER.PROVIDERS`;

-- 3. full load by Inserting merged Data 
INSERT INTO `DP_BASE_SILVER.PROVIDERS`
SELECT DISTINCT 
    ProviderID,
    FirstName,
    LastName,
    Specialization,
    DeptID,
    CAST(NPI AS INT64) AS NPI,
    datasource,
    CASE 
        WHEN ProviderID IS NULL OR DeptID IS NULL THEN TRUE 
        ELSE FALSE 
    END AS is_quarantined
FROM (
    SELECT DISTINCT *, 'hosa' AS datasource FROM `DP_BASE_BRONZE.PROVIDERS_HA`
    UNION ALL
    SELECT DISTINCT *, 'hosb' AS datasource FROM `DP_BASE_BRONZE.PROVIDERS_HB`
);


END;