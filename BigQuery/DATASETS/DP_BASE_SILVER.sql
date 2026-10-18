CREATE SCHEMA IF NOT EXISTS DP_BASE_SILVER
OPTIONS(
    location = 'us-central1',
    description = 'This dataset is used to store transformed tables.',
    labels = [
        ("env", "dev"),
        ("team", "data-platform")
    ]
)