-- =============================================================
-- RetailPulse — Staging Layer Views
-- Dataset: retailpulse-509504.retailpulse_staging
-- =============================================================

-- 1. stg_orders
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_orders` AS
SELECT
    order_id, customer_id, order_status,
    TIMESTAMP(order_purchase_timestamp) AS order_purchase_timestamp,
    TIMESTAMP(order_approved_at) AS order_approved_at,
    TIMESTAMP(order_delivered_carrier_date) AS order_delivered_carrier_date,
    TIMESTAMP(order_delivered_customer_date) AS order_delivered_customer_date,
    TIMESTAMP(order_estimated_delivery_date) AS order_estimated_delivery_date,
    DATE_DIFF(DATE(order_delivered_customer_date), DATE(order_purchase_timestamp), DAY) AS delivery_days_actual,
    DATE_DIFF(DATE(order_estimated_delivery_date), DATE(order_purchase_timestamp), DAY) AS delivery_days_estimated
FROM `retailpulse-509504.retailpulse_raw.orders`;

-- 2. stg_customers
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_customers` AS
SELECT
    customer_id, customer_unique_id,
    customer_zip_code_prefix AS zip_code,
    customer_city AS city,
    customer_state AS state
FROM `retailpulse-509504.retailpulse_raw.customers`;

-- 3. stg_order_items
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_order_items` AS
SELECT
    order_id, order_item_id, product_id, seller_id,
    TIMESTAMP(shipping_limit_date) AS shipping_limit_date,
    ROUND(CAST(price AS FLOAT64), 2) AS price,
    ROUND(CAST(freight_value AS FLOAT64), 2) AS freight_value
FROM `retailpulse-509504.retailpulse_raw.order_items`;

-- 4. stg_order_payments
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_order_payments` AS
SELECT
    order_id, payment_sequential, payment_type,
    CAST(payment_installments AS INT64) AS payment_installments,
    ROUND(CAST(payment_value AS FLOAT64), 2) AS payment_value
FROM `retailpulse-509504.retailpulse_raw.order_payments`;

-- 5. stg_order_reviews
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_order_reviews` AS
SELECT
    review_id, order_id,
    CAST(review_score AS INT64) AS review_score,
    review_comment_title, review_comment_message,
    TIMESTAMP(review_creation_date) AS review_creation_date,
    TIMESTAMP(review_answer_timestamp) AS review_answer_timestamp,
    CASE WHEN review_score <= 2 THEN TRUE ELSE FALSE END AS is_low_review,
    CASE WHEN review_comment_message IS NOT NULL AND TRIM(review_comment_message) != '' THEN TRUE ELSE FALSE END AS has_comment
FROM `retailpulse-509504.retailpulse_raw.order_reviews`;

-- 6. stg_products
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_products` AS
SELECT
    product_id, product_category_name,
    CAST(product_name_length AS INT64) AS product_name_length,
    CAST(product_description_length AS INT64) AS product_description_length,
    CAST(product_photos_qty AS INT64) AS product_photos_qty,
    ROUND(CAST(product_weight_g AS FLOAT64), 2) AS product_weight_g,
    ROUND(CAST(product_length_cm AS FLOAT64), 2) AS product_length_cm,
    ROUND(CAST(product_height_cm AS FLOAT64), 2) AS product_height_cm,
    ROUND(CAST(product_width_cm AS FLOAT64), 2) AS product_width_cm
FROM `retailpulse-509504.retailpulse_raw.products`;

-- 7. stg_sellers
CREATE OR REPLACE VIEW `retailpulse-509504.retailpulse_staging.stg_sellers` AS
SELECT
    seller_id,
    seller_zip_code_prefix AS zip_code,
    seller_city AS city,
    seller_state AS state
FROM `retailpulse-509504.retailpulse_raw.sellers`;
