# ingestion/upload_to_gcs.py
from google.cloud import storage
import os
from pathlib import Path
from loguru import logger

PROJECT_ID  = "retailpulse-509504"
BUCKET_NAME = "retailpulse-raw-data-retailpulse-509504"
LOCAL_RAW   = Path("data/raw")

# Map: local filename → GCS folder
FILE_MAP = {
    "olist_orders_dataset.csv":            "raw/orders/",
    "olist_order_items_dataset.csv":       "raw/order_items/",
    "olist_order_payments_dataset.csv":    "raw/order_payments/",
    "olist_order_reviews_dataset.csv":     "raw/order_reviews/",
    "olist_customers_dataset.csv":         "raw/customers/",
    "olist_sellers_dataset.csv":           "raw/sellers/",
    "olist_products_dataset.csv":          "raw/products/",
    "olist_geolocation_dataset.csv":       "raw/geolocation/",
    "product_category_name_translation.csv": "raw/category_translation/",
}

def upload_all():
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)

    for filename, gcs_folder in FILE_MAP.items():
        local_path = LOCAL_RAW / filename
        gcs_path   = gcs_folder + filename

        if not local_path.exists():
            logger.error(f"Missing: {local_path}")
            continue

        logger.info(f"Uploading {filename} → gs://{BUCKET_NAME}/{gcs_path}")
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        logger.success(f"  ✓ Done ({local_path.stat().st_size / 1e6:.1f} MB)")

    logger.success("All files uploaded!")

if __name__ == "__main__":
    upload_all()