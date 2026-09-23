-- sql/problems/01_revenue_by_month.sql
SELECT
  DATE_TRUNC(DATE(o.order_purchase_timestamp), MONTH) AS order_month,
  COUNT(DISTINCT o.order_id)                          AS total_orders,
  ROUND(SUM(p.payment_value), 2)                      AS total_revenue
FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` p
  ON o.order_id = p.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY order_month
ORDER BY order_month;



-- sql/problems/02_top_categories_by_revenue.sql
SELECT
  p.category_en,
  COUNT(DISTINCT i.order_id)  AS order_count,
  ROUND(SUM(i.price), 2)      AS total_revenue,
  ROUND(AVG(i.price), 2)      AS avg_price
FROM `retailpulse-509504.retailpulse_staging.stg_order_items` i
JOIN `retailpulse-509504.retailpulse_staging.stg_products` p
  ON i.product_id = p.product_id
GROUP BY p.category_en
ORDER BY total_revenue DESC
LIMIT 10;




-- sql/problems/03_avg_delivery_by_state.sql
SELECT
  c.state,
  COUNT(DISTINCT o.order_id)             AS total_orders,
  ROUND(AVG(o.delivery_days_actual), 1)  AS avg_delivery_days,
  ROUND(MIN(o.delivery_days_actual), 1)  AS min_delivery_days,
  ROUND(MAX(o.delivery_days_actual), 1)  AS max_delivery_days
FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
JOIN `retailpulse-509504.retailpulse_staging.stg_customers` c
  ON o.customer_id = c.customer_id
WHERE o.delivery_days_actual IS NOT NULL
  AND o.delivery_days_actual > 0
  AND o.order_status = 'delivered'
GROUP BY c.state
ORDER BY avg_delivery_days DESC;




-- sql/problems/04_order_status_distribution.sql
SELECT
  order_status,
  COUNT(*)                                                      AS order_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)           AS pct_of_total
FROM `retailpulse-509504.retailpulse_staging.stg_orders`
GROUP BY order_status
ORDER BY order_count DESC;




-- sql/problems/05_review_score_analysis.sql
SELECT
  o.order_status,
  r.review_score,
  COUNT(*)                                                                          AS review_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY o.order_status), 2)   AS pct_within_status
FROM `retailpulse-509504.retailpulse_staging.stg_order_reviews` r
JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
  ON r.order_id = o.order_id
WHERE o.order_status IN ('delivered', 'canceled', 'shipped')
GROUP BY o.order_status, r.review_score
ORDER BY o.order_status, r.review_score;