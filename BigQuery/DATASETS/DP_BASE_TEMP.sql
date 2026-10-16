CREATE SCHEMA IF NOT EXISTS DP_BASE_TEMP
OPTIONS(
    location = 'us-central1',
    description = 'This dataset is used to store temporary tables for DP_BASE queries.',
    labels = [
        ("env", "dev"),
        ("team", "data-platform")
    ]
)