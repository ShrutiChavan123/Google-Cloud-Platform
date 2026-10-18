CREATE SCHEMA IF NOT EXISTS DP_BASE_BACKUP
OPTIONS(
    location = 'us-central1',
    description = 'This dataset stores backup data for DP_BASE_GOLD datasets.',
    labels = [
        ("env", "dev"),
        ("team", "data-platform")
    ]
);
