# ingestion/load_raw_to_bigquery.py
from google.cloud import bigquery
from loguru import logger
import sys

PROJECT_ID = "retailpulse-509504"
DATASET    = "retailpulse_raw"
GCS_BUCKET = "retailpulse-raw-data-retailpulse-509504"

TABLES = [
    {
        "table": "raw_orders",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/orders/*.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("order_status", "STRING"),
            bigquery.SchemaField("order_purchase_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("order_approved_at", "TIMESTAMP"),
            bigquery.SchemaField("order_delivered_carrier_date", "TIMESTAMP"),
            bigquery.SchemaField("order_delivered_customer_date", "TIMESTAMP"),
            bigquery.SchemaField("order_estimated_delivery_date", "TIMESTAMP"),
        ],
    },
    {
        "table": "raw_order_items",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/order_items/*.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("order_item_id", "INTEGER"),
            bigquery.SchemaField("product_id", "STRING"),
            bigquery.SchemaField("seller_id", "STRING"),
            bigquery.SchemaField("shipping_limit_date", "TIMESTAMP"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("freight_value", "FLOAT"),
        ],
    },
    {
        "table": "raw_order_payments",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/order_payments/*.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("payment_sequential", "INTEGER"),
            bigquery.SchemaField("payment_type", "STRING"),
            bigquery.SchemaField("payment_installments", "INTEGER"),
            bigquery.SchemaField("payment_value", "FLOAT"),
        ],
    },
    {
        "table": "raw_order_reviews",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/order_reviews/*.csv",
        "schema": [
            bigquery.SchemaField("review_id", "STRING"),
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("review_score", "INTEGER"),
            bigquery.SchemaField("review_comment_title", "STRING"),
            bigquery.SchemaField("review_comment_message", "STRING"),
            bigquery.SchemaField("review_creation_date", "TIMESTAMP"),
            bigquery.SchemaField("review_answer_timestamp", "TIMESTAMP"),
        ],
    },
    {
        "table": "raw_customers",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/customers/*.csv",
        "schema": [
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("customer_unique_id", "STRING"),
            bigquery.SchemaField("customer_zip_code_prefix", "STRING"),
            bigquery.SchemaField("customer_city", "STRING"),
            bigquery.SchemaField("customer_state", "STRING"),
        ],
    },
    {
        "table": "raw_sellers",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/sellers/*.csv",
        "schema": [
            bigquery.SchemaField("seller_id", "STRING"),
            bigquery.SchemaField("seller_zip_code_prefix", "STRING"),
            bigquery.SchemaField("seller_city", "STRING"),
            bigquery.SchemaField("seller_state", "STRING"),
        ],
    },
    {
        "table": "raw_products",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/products/*.csv",
        "schema": [
            bigquery.SchemaField("product_id", "STRING"),
            bigquery.SchemaField("product_category_name", "STRING"),
            bigquery.SchemaField("product_name_lenght", "INTEGER"),
            bigquery.SchemaField("product_description_lenght", "INTEGER"),
            bigquery.SchemaField("product_photos_qty", "INTEGER"),
            bigquery.SchemaField("product_weight_g", "FLOAT"),
            bigquery.SchemaField("product_length_cm", "FLOAT"),
            bigquery.SchemaField("product_height_cm", "FLOAT"),
            bigquery.SchemaField("product_width_cm", "FLOAT"),
        ],
    },
    {
        "table": "raw_geolocation",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/geolocation/*.csv",
        "schema": [
            bigquery.SchemaField("geolocation_zip_code_prefix", "STRING"),
            bigquery.SchemaField("geolocation_lat", "FLOAT"),
            bigquery.SchemaField("geolocation_lng", "FLOAT"),
            bigquery.SchemaField("geolocation_city", "STRING"),
            bigquery.SchemaField("geolocation_state", "STRING"),
        ],
    },
    {
        "table": "raw_category_translation",
        "gcs_uri": f"gs://{GCS_BUCKET}/raw/category_translation/*.csv",
        "schema": [
            bigquery.SchemaField("product_category_name", "STRING"),
            bigquery.SchemaField("product_category_name_english", "STRING"),
        ],
    },
]


def load_table(client, config):
    table_ref = f"{PROJECT_ID}.{DATASET}.{config['table']}"
    job_config = bigquery.LoadJobConfig(
        schema=config["schema"],
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition="WRITE_TRUNCATE",
        allow_quoted_newlines=True,
        allow_jagged_rows=True,
    )
    logger.info(f"Loading {config['table']} ...")
    load_job = client.load_table_from_uri(
        config["gcs_uri"], table_ref, job_config=job_config
    )
    load_job.result()
    table = client.get_table(table_ref)
    logger.success(f"  ✓ {config['table']}: {table.num_rows:,} rows")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    logger.info(f"Loading raw tables into {PROJECT_ID}.{DATASET}")
    errors = []
    for config in TABLES:
        try:
            load_table(client, config)
        except Exception as e:
            logger.error(f"  ✗ {config['table']}: {e}")
            errors.append(config["table"])
    if errors:
        logger.error(f"Failed: {errors}")
        sys.exit(1)
    logger.success("✓ All raw tables loaded!")


if __name__ == "__main__":
    main()