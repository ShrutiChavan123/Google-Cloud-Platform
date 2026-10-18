CREATE SCHEMA IF NOT EXISTS DP_BASE_GOLD
OPTIONS(
    location = 'us-central1',
    description = 'This dataset is used to store final, processed business tables.',
    labels = [
        ("env", "dev"),
        ("team", "data-platform")
    ]
)