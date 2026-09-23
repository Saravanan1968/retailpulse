-- sql/mart/feature_customer_360.sql
CREATE OR REPLACE TABLE `retailpulse-509504.retailpulse_mart.feature_customer_360` AS

WITH reference_date AS (
  SELECT MAX(DATE(order_purchase_timestamp)) AS ref_date
  FROM `retailpulse-509504.retailpulse_staging.stg_orders`
),

-- Feature group 1: RFM
rfm AS (
  SELECT
    c.customer_unique_id,
    DATE_DIFF(rd.ref_date, MAX(DATE(o.order_purchase_timestamp)), DAY) AS recency_days,
    COUNT(DISTINCT o.order_id)    AS frequency,
    ROUND(SUM(p.payment_value), 2) AS monetary
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` p ON o.order_id = p.order_id
  CROSS JOIN reference_date rd
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
  GROUP BY c.customer_unique_id, rd.ref_date
),

-- Feature group 2: Review behavior
review_features AS (
  SELECT
    c.customer_unique_id,
    ROUND(AVG(r.review_score), 2)                     AS avg_review_score,
    COUNTIF(r.review_score <= 2)                      AS low_review_count,
    COUNTIF(r.has_comment = TRUE)                     AS reviews_with_comment
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_reviews` r ON o.order_id = r.order_id
  GROUP BY c.customer_unique_id
),

-- Feature group 3: Delivery behavior
delivery_features AS (
  SELECT
    c.customer_unique_id,
    ROUND(AVG(o.delivery_days_actual), 1)              AS avg_delivery_days,
    ROUND(AVG(o.delivery_days_actual - o.delivery_days_estimated), 1) AS avg_delay_days,
    ROUND(SAFE_DIVIDE(
      COUNTIF(o.delivery_days_actual > o.delivery_days_estimated),
      COUNT(DISTINCT o.order_id)
    ), 3)                                              AS pct_late_deliveries
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  WHERE o.order_status = 'delivered'
    AND o.delivery_days_actual IS NOT NULL
  GROUP BY c.customer_unique_id
),

-- Feature group 4: Product diversity
product_features AS (
  SELECT
    c.customer_unique_id,
    COUNT(DISTINCT p.category_en)   AS distinct_categories,
    COUNT(DISTINCT i.product_id)    AS distinct_products
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_items` i ON o.order_id = i.order_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_products` p ON i.product_id = p.product_id
  GROUP BY c.customer_unique_id
),

-- Feature group 5: Payment behavior
payment_features AS (
  SELECT
    c.customer_unique_id,
    MAX(pay.payment_installments)   AS max_installments,
    COUNT(DISTINCT pay.payment_type) AS distinct_payment_types
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` pay ON o.order_id = pay.order_id
  GROUP BY c.customer_unique_id
),

-- Churn label
churn_labels AS (
  SELECT
    c.customer_unique_id,
    MAX(DATE(o.order_purchase_timestamp)) AS last_order_date,
    CASE
      WHEN DATE_DIFF(rd.ref_date, MAX(DATE(o.order_purchase_timestamp)), DAY) > 180
       AND COUNT(DISTINCT o.order_id) = 1
      THEN TRUE
      ELSE FALSE
    END AS churned
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o ON c.customer_id = o.customer_id
  CROSS JOIN reference_date rd
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
  GROUP BY c.customer_unique_id, rd.ref_date
)

-- Final join: one row per unique customer
SELECT
  r.customer_unique_id,
  r.recency_days,
  r.frequency,
  r.monetary,
  COALESCE(rv.avg_review_score, 3.0)   AS avg_review_score,
  COALESCE(rv.low_review_count, 0)     AS low_review_count,
  COALESCE(rv.reviews_with_comment, 0) AS reviews_with_comment,
  COALESCE(d.avg_delivery_days, 0)     AS avg_delivery_days,
  COALESCE(d.avg_delay_days, 0)        AS avg_delay_days,
  COALESCE(d.pct_late_deliveries, 0)   AS pct_late_deliveries,
  COALESCE(pf.distinct_categories, 1)  AS distinct_categories,
  COALESCE(pf.distinct_products, 1)    AS distinct_products,
  COALESCE(py.max_installments, 1)     AS max_installments,
  COALESCE(py.distinct_payment_types, 1) AS distinct_payment_types,
  cl.churned
FROM rfm r
LEFT JOIN review_features rv    ON r.customer_unique_id = rv.customer_unique_id
LEFT JOIN delivery_features d   ON r.customer_unique_id = d.customer_unique_id
LEFT JOIN product_features pf   ON r.customer_unique_id = pf.customer_unique_id
LEFT JOIN payment_features py   ON r.customer_unique_id = py.customer_unique_id
LEFT JOIN churn_labels cl       ON r.customer_unique_id = cl.customer_unique_id;