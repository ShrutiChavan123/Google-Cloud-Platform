CREATE SCHEMA IF NOT EXISTS DP_BASE_BRONZE
OPTIONS(
    location = 'us-central1',
    description = 'This dataset stores raw source data in the Bronze layer.',
    labels = [
        ("env", "dev"),
        ("team", "data-platform")
    ]
);
