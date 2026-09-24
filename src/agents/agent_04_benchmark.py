# src/agents/agent_04_benchmark.py
"""
Benchmark Agent: Compares a customer's delivery/review metrics
against their state cohort average from BigQuery.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from google.cloud import bigquery
from loguru import logger

PROJECT_ID = "retailpulse-509504"
client     = bigquery.Client(project=PROJECT_ID)


def get_cohort_benchmark(customer_unique_id: str) -> dict:
    """
    Fetch customer's state and compare their delivery/review metrics
    against the state cohort average.
    """
    query = """
    WITH customer_state AS (
        SELECT
            c.customer_unique_id,
            c.state,
            f.avg_delivery_days      AS cust_avg_delivery,
            f.avg_delay_days         AS cust_avg_delay,
            f.avg_review_score       AS cust_avg_review,
            f.pct_late_deliveries    AS cust_pct_late,
            f.monetary               AS cust_monetary
        FROM `retailpulse-509504.retailpulse_mart.feature_customer_360` f
        JOIN `retailpulse-509504.retailpulse_mart.dim_customers` c
            USING (customer_unique_id)
        WHERE f.customer_unique_id = @customer_unique_id
    ),
    cohort_avg AS (
        SELECT
            c2.state,
            ROUND(AVG(f2.avg_delivery_days), 1)   AS cohort_avg_delivery,
            ROUND(AVG(f2.avg_delay_days), 1)       AS cohort_avg_delay,
            ROUND(AVG(f2.avg_review_score), 2)     AS cohort_avg_review,
            ROUND(AVG(f2.pct_late_deliveries), 3)  AS cohort_pct_late,
            ROUND(AVG(f2.monetary), 2)             AS cohort_avg_monetary,
            COUNT(DISTINCT f2.customer_unique_id)  AS cohort_size
        FROM `retailpulse-509504.retailpulse_mart.feature_customer_360` f2
        JOIN `retailpulse-509504.retailpulse_mart.dim_customers` c2
            USING (customer_unique_id)
        WHERE c2.state = (SELECT state FROM customer_state)
        GROUP BY c2.state
    )
    SELECT
        cs.*,
        ca.cohort_avg_delivery,
        ca.cohort_avg_delay,
        ca.cohort_avg_review,
        ca.cohort_pct_late,
        ca.cohort_avg_monetary,
        ca.cohort_size,
        ROUND(cs.cust_avg_delivery - ca.cohort_avg_delivery, 1) AS delivery_vs_cohort,
        ROUND(cs.cust_avg_review   - ca.cohort_avg_review,   2) AS review_vs_cohort
    FROM customer_state cs, cohort_avg ca
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("customer_unique_id", "STRING", customer_unique_id)
        ]
    )

    logger.info(f"Fetching cohort benchmark for customer {customer_unique_id[:8]}...")
    rows = list(client.query(query, job_config=job_config).result())

    if not rows:
        logger.warning("No benchmark data found — customer may not be in dim_customers")
        return {}

    row = dict(rows[0])
    logger.success(
        f"State: {row['state']} | Cohort size: {row['cohort_size']:,} | "
        f"Delivery vs cohort: {row['delivery_vs_cohort']:+.1f} days"
    )
    return row


if __name__ == "__main__":
    from google.cloud import bigquery as bq

    # Get a sample customer
    sample = list(bq.Client(project=PROJECT_ID).query("""
        SELECT customer_unique_id FROM `retailpulse-509504.retailpulse_mart.dim_customers`
        WHERE total_orders >= 1 LIMIT 1
    """).result())[0]

    result = get_cohort_benchmark(sample['customer_unique_id'])

    print("\n── Benchmark Agent Result ──")
    print(f"Customer state      : {result.get('state')}")
    print(f"Cohort size         : {result.get('cohort_size'):,}")
    print(f"Cust delivery days  : {result.get('cust_avg_delivery')}")
    print(f"Cohort delivery avg : {result.get('cohort_avg_delivery')}")
    print(f"Delivery vs cohort  : {result.get('delivery_vs_cohort'):+.1f} days")
    print(f"Cust review score   : {result.get('cust_avg_review')}")
    print(f"Cohort review avg   : {result.get('cohort_avg_review')}")
    print(f"Review vs cohort    : {result.get('review_vs_cohort'):+.2f}")