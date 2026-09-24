# src/data/loader.py
"""Pull feature_customer_360 from BigQuery into a pandas DataFrame."""

from google.cloud import bigquery
import pandas as pd
from loguru import logger

PROJECT_ID = "retailpulse-509504"
TABLE      = "retailpulse-509504.retailpulse_mart.feature_customer_360"


def load_features(table: str = TABLE) -> pd.DataFrame:
    """Load the ML feature table from BigQuery."""
    client = bigquery.Client(project=PROJECT_ID)
    logger.info(f"Loading features from {table} ...")
    query = f"SELECT * FROM `{table}`"
    df = client.query(query).to_dataframe()
    logger.success(f"Loaded {len(df):,} rows, {df.shape[1]} columns")
    return df


def get_features_and_target(df: pd.DataFrame):
    """Split into X (features) and y (target)."""
    target_col  = "churned"
    drop_cols   = ["customer_unique_id", "churned"]

    X = df.drop(columns=drop_cols)
    y = df[target_col].astype(int)

    logger.info(f"Features: {X.columns.tolist()}")
    logger.info(f"Target distribution:\n{y.value_counts(normalize=True).round(3)}")
    return X, y


if __name__ == "__main__":
    df = load_features()
    print(df.head())
    print(df.dtypes)
    print(df.isnull().sum())