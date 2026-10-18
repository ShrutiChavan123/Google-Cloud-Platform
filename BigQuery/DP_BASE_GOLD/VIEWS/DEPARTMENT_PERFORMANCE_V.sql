CREATE OR REPLACE VIEW DP_BASE_GOLD_V.DEPARTMENT_PERFORMANCE_V 
OPTIONS(
    description = 'This view provides a department-level performance summary, including total encounters, transactions, billed and paid amounts, and average payment per transaction.'
)
AS
SELECT * FROM DP_BASE_GOLD.DEPARTMENT_PERFORMANCE;