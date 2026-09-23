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



-- sql/problems/07_cohort_retention.sql
/*
  Cohort retention: % of customers from each acquisition month
  who placed another order in subsequent months.
  Key concepts: DATE_TRUNC, DATE_DIFF on months, window functions.
*/
WITH first_orders AS (
  SELECT
    c.customer_unique_id,
    DATE_TRUNC(MIN(DATE(o.order_purchase_timestamp)), MONTH) AS cohort_month
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
    ON c.customer_id = o.customer_id
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
  GROUP BY c.customer_unique_id
),
all_orders AS (
  SELECT
    c.customer_unique_id,
    DATE_TRUNC(DATE(o.order_purchase_timestamp), MONTH) AS order_month
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
    ON c.customer_id = o.customer_id
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
  GROUP BY c.customer_unique_id, order_month
),
cohort_activity AS (
  SELECT
    f.cohort_month,
    DATE_DIFF(a.order_month, f.cohort_month, MONTH) AS months_since_first,
    COUNT(DISTINCT a.customer_unique_id)             AS active_customers
  FROM first_orders f
  JOIN all_orders a USING (customer_unique_id)
  GROUP BY f.cohort_month, months_since_first
),
cohort_sizes AS (
  SELECT cohort_month, COUNT(*) AS cohort_size
  FROM first_orders
  GROUP BY cohort_month
)
SELECT
  ca.cohort_month,
  cs.cohort_size,
  ca.months_since_first,
  ca.active_customers,
  ROUND(ca.active_customers * 100.0 / cs.cohort_size, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs USING (cohort_month)
WHERE ca.cohort_month BETWEEN '2017-01-01' AND '2018-06-01'
ORDER BY ca.cohort_month, ca.months_since_first;





-- sql/problems/08_seller_performance_ranking.sql
/*
  Rank sellers within each state by avg review score.
  Key concepts: RANK() OVER (PARTITION BY ... ORDER BY ...).
*/
WITH seller_stats AS (
  SELECT
    i.seller_id,
    s.state,
    COUNT(DISTINCT o.order_id)          AS total_orders,
    ROUND(AVG(r.review_score), 2)       AS avg_review_score,
    ROUND(AVG(
      CASE WHEN o.delivery_days_actual > o.delivery_days_estimated
           THEN 1.0 ELSE 0.0 END
    ) * 100, 1)                         AS late_delivery_pct
  FROM `retailpulse-509504.retailpulse_staging.stg_order_items` i
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
    ON i.order_id = o.order_id
  JOIN `retailpulse-509504.retailpulse_staging.stg_sellers` s
    ON i.seller_id = s.seller_id
  LEFT JOIN `retailpulse-509504.retailpulse_staging.stg_order_reviews` r
    ON o.order_id = r.order_id
  WHERE o.order_status = 'delivered'
    AND o.delivery_days_actual IS NOT NULL
  GROUP BY i.seller_id, s.state
  HAVING total_orders >= 10  -- minimum volume threshold
)
SELECT
  seller_id,
  state,
  total_orders,
  avg_review_score,
  late_delivery_pct,
  RANK() OVER (PARTITION BY state ORDER BY avg_review_score DESC) AS rank_in_state,
  RANK() OVER (ORDER BY avg_review_score DESC)                    AS rank_overall
FROM seller_stats
ORDER BY state, rank_in_state;







-- sql/problems/09_rolling_revenue.sql
/*
  Daily revenue with 7-day and 30-day rolling averages.
  Key concepts: window frame (ROWS BETWEEN N PRECEDING AND CURRENT ROW).
*/
WITH daily_revenue AS (
  SELECT
    DATE(o.order_purchase_timestamp)  AS order_date,
    ROUND(SUM(p.payment_value), 2)    AS daily_revenue
  FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` p
    ON o.order_id = p.order_id
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
  GROUP BY order_date
)
SELECT
  order_date,
  daily_revenue,
  ROUND(AVG(daily_revenue) OVER (
    ORDER BY order_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_7d_avg,
  ROUND(AVG(daily_revenue) OVER (
    ORDER BY order_date
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_30d_avg
FROM daily_revenue
ORDER BY order_date;





-- sql/problems/10_seller_delay_pct.sql
/*
  What % of each seller's orders were delivered late?
  Key concepts: COUNTIF, SAFE_DIVIDE, aggregation.
*/
SELECT
  i.seller_id,
  COUNT(DISTINCT o.order_id)                    AS total_orders,
  COUNTIF(o.delivery_days_actual > o.delivery_days_estimated) AS late_orders,
  ROUND(
    SAFE_DIVIDE(
      COUNTIF(o.delivery_days_actual > o.delivery_days_estimated),
      COUNT(DISTINCT o.order_id)
    ) * 100, 2
  )                                              AS late_delivery_pct,
  ROUND(AVG(
    o.delivery_days_actual - o.delivery_days_estimated
  ), 1)                                          AS avg_delay_days
FROM `retailpulse-509504.retailpulse_staging.stg_order_items` i
JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
  ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.delivery_days_actual IS NOT NULL
  AND o.delivery_days_estimated IS NOT NULL
GROUP BY i.seller_id
HAVING total_orders >= 20
ORDER BY late_delivery_pct DESC;





-- sql/problems/11_churn_label.sql
/*
  Generate churn label per unique customer.
  Churn = no repeat order within 180 days of last order
          AND account age > 180 days (exclude too-new customers).
  Key concepts: LEAD(), DATE_DIFF, QUALIFY.
*/
WITH customer_orders AS (
  SELECT
    c.customer_unique_id,
    DATE(o.order_purchase_timestamp)  AS order_date,
    LEAD(DATE(o.order_purchase_timestamp)) OVER (
      PARTITION BY c.customer_unique_id
      ORDER BY o.order_purchase_timestamp
    )                                 AS next_order_date
  FROM `retailpulse-509504.retailpulse_staging.stg_customers` c
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
    ON c.customer_id = o.customer_id
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
last_orders AS (
  -- keep only each customer's most recent order
  SELECT *
  FROM customer_orders
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_unique_id ORDER BY order_date DESC
  ) = 1
),
reference_date AS (
  SELECT MAX(order_date) AS ref_date FROM last_orders
)
SELECT
  lo.customer_unique_id,
  lo.order_date   AS last_order_date,
  lo.next_order_date,
  DATE_DIFF(rd.ref_date, lo.order_date, DAY) AS days_since_last_order,
  -- account age = days since first order
  DATE_DIFF(rd.ref_date, lo.order_date, DAY) AS account_age_days,
  CASE
    -- churned: no next order AND account is old enough to evaluate
    WHEN lo.next_order_date IS NULL
     AND DATE_DIFF(rd.ref_date, lo.order_date, DAY) > 180
    THEN TRUE
    ELSE FALSE
  END AS churned
FROM last_orders lo
CROSS JOIN reference_date rd;






-- sql/problems/12_seller_late_anomaly.sql
/*
  Sellers whose late-delivery rate this month is >2 std-dev
  above their trailing 6-month average.
  Key concepts: AVG/STDDEV OVER, RANGE window, CTE chain.
*/
WITH monthly_late AS (
  SELECT
    i.seller_id,
    DATE_TRUNC(DATE(o.order_purchase_timestamp), MONTH) AS order_month,
    COUNT(DISTINCT o.order_id)                          AS total_orders,
    ROUND(
      SAFE_DIVIDE(
        COUNTIF(o.delivery_days_actual > o.delivery_days_estimated),
        COUNT(DISTINCT o.order_id)
      ) * 100, 2
    )                                                   AS late_pct
  FROM `retailpulse-509504.retailpulse_staging.stg_order_items` i
  JOIN `retailpulse-509504.retailpulse_staging.stg_orders` o
    ON i.order_id = o.order_id
  WHERE o.order_status = 'delivered'
    AND o.delivery_days_actual IS NOT NULL
  GROUP BY i.seller_id, order_month
  HAVING total_orders >= 5
),
with_stats AS (
  SELECT
    seller_id,
    order_month,
    late_pct,
    total_orders,
    AVG(late_pct) OVER (
      PARTITION BY seller_id
      ORDER BY order_month
      ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS trailing_6m_avg,
    STDDEV(late_pct) OVER (
      PARTITION BY seller_id
      ORDER BY order_month
      ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS trailing_6m_stddev
  FROM monthly_late
)
SELECT
  seller_id,
  order_month,
  late_pct,
  ROUND(trailing_6m_avg, 2)    AS trailing_avg,
  ROUND(trailing_6m_stddev, 2) AS trailing_stddev,
  ROUND(
    SAFE_DIVIDE(late_pct - trailing_6m_avg, trailing_6m_stddev), 2
  )                            AS z_score
FROM with_stats
WHERE trailing_6m_avg IS NOT NULL
  AND trailing_6m_stddev > 0
  AND SAFE_DIVIDE(late_pct - trailing_6m_avg, trailing_6m_stddev) > 2
ORDER BY z_score DESC;





-- sql/problems/13_seller_review_trend.sql
/*
  Review score trend per seller: raw → weekly avg → 4-week moving avg.
  Key concepts: chained CTEs, DATE_TRUNC(WEEK), window over weeks.
*/
WITH raw_reviews AS (
  SELECT
    i.seller_id,
    DATE_TRUNC(DATE(r.review_creation_date), WEEK) AS review_week,
    r.review_score
  FROM `retailpulse-509504.retailpulse_staging.stg_order_reviews` r
  JOIN `retailpulse-509504.retailpulse_staging.stg_order_items` i
    ON r.order_id = i.order_id
),
weekly_avg AS (
  SELECT
    seller_id,
    review_week,
    COUNT(*)                      AS review_count,
    ROUND(AVG(review_score), 3)   AS weekly_avg_score
  FROM raw_reviews
  GROUP BY seller_id, review_week
  HAVING review_count >= 3
),
moving_avg AS (
  SELECT
    seller_id,
    review_week,
    review_count,
    weekly_avg_score,
    ROUND(AVG(weekly_avg_score) OVER (
      PARTITION BY seller_id
      ORDER BY review_week
      ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ), 3) AS score_4wk_moving_avg
  FROM weekly_avg
)
SELECT *
FROM moving_avg
ORDER BY seller_id, review_week;





