import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from google.cloud import bigquery
from loguru import logger

PROJECT_ID = "retailpulse-509504"
client     = bigquery.Client(project=PROJECT_ID)

# Only these templates are allowed - agents never run freeform SQL
QUERY_TEMPLATES = {
    "customer_order_history": """
        SELECT
          o.order_id,
          DATE(o.order_purchase_timestamp)    AS order_date,
          o.order_status,
          ROUND(p.payment_value, 2)           AS payment_value,
          o.delivery_days_actual,
          o.delivery_days_estimated,
          o.delivery_days_actual - o.delivery_days_estimated AS delay_days,
          r.review_score
        FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
        LEFT JOIN `retailpulse-509504.retailpulse_staging.stg_order_payments` p
          ON o.order_id = p.order_id
        LEFT JOIN `retailpulse-509504.retailpulse_staging.stg_order_reviews` r
          ON o.order_id = r.order_id
        JOIN `retailpulse-509504.retailpulse_staging.stg_customers` c
          ON o.customer_id = c.customer_id
        WHERE c.customer_unique_id = @customer_unique_id
        ORDER BY o.order_purchase_timestamp DESC
        LIMIT 20
    """,
    "cohort_avg_delivery": """
        SELECT
          c.state,
          ROUND(AVG(o.delivery_days_actual), 1) AS avg_delivery_days,
          ROUND(AVG(o.delivery_days_actual - o.delivery_days_estimated), 1) AS avg_delay_days,
          COUNT(DISTINCT o.order_id) AS total_orders
        FROM `retailpulse-509504.retailpulse_staging.stg_orders` o
        JOIN `retailpulse-509504.retailpulse_staging.stg_customers` c
          ON o.customer_id = c.customer_id
        WHERE c.state = @state
          AND o.order_status = 'delivered'
        GROUP BY c.state
    """
}


def run_query(template_name: str, params: dict) -> list[dict]:
    """Run a pre-approved SQL template with the given parameters."""
    if template_name not in QUERY_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}. "
                         f"Allowed: {list(QUERY_TEMPLATES.keys())}")

    query = QUERY_TEMPLATES[template_name]

    bq_params = [
        bigquery.ScalarQueryParameter(k, "STRING", v)
        for k, v in params.items()
    ]
    job_config = bigquery.QueryJobConfig(query_parameters=bq_params)

    logger.info(f"Running template: {template_name} | params: {params}")
    rows = client.query(query, job_config=job_config).result()
    results = [dict(row) for row in rows]
    logger.success(f"Returned {len(results)} rows")
    return results


if __name__ == "__main__":
    sample = list(client.query("""
        SELECT customer_unique_id
        FROM `retailpulse-509504.retailpulse_mart.dim_customers`
        WHERE total_orders >= 1
        LIMIT 1
    """).result())[0]
    cuid = sample['customer_unique_id']

    print(f"Fetching order history for customer: {cuid[:8]}...")
    history = run_query("customer_order_history", {"customer_unique_id": cuid})

    print(f"\nExperiment 2 Result: {len(history)} orders found")
    for order in history:
        print(f"  {order['order_date']} | {order['order_status']:12s} | "
              f"R${order['payment_value']} | "
              f"Delivery: {order['delivery_days_actual']} days | "
              f"Delay: {order['delay_days']} | "
              f"Review: {order['review_score']}")
