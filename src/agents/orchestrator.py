import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import argparse
import json
import requests
from datetime import datetime
from loguru import logger
from google.cloud import bigquery

from src.agents.experiment_02_bigquery_agent import run_query
from src.agents.experiment_04_shap_interpreter import explain_churn_score
from src.agents.agent_04_benchmark import get_cohort_benchmark
from src.agents.agent_05_recommendation import generate_recommendations

PROJECT_ID  = "retailpulse-509504"
PREDICT_URL = "http://localhost:8000/predict"
client      = bigquery.Client(project=PROJECT_ID)


def get_customer_features(customer_unique_id: str) -> dict | None:
    """Pull the feature row for a given customer from the mart table."""
    query = """
    SELECT
        monetary, avg_review_score, low_review_count, reviews_with_comment,
        avg_delivery_days, avg_delay_days, pct_late_deliveries,
        distinct_categories, distinct_products, max_installments,
        distinct_payment_types
    FROM `retailpulse-509504.retailpulse_mart.feature_customer_360`
    WHERE customer_unique_id = @customer_unique_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("customer_unique_id", "STRING", customer_unique_id)
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        return None
    row = dict(rows[0])
    # BigQuery returns Decimal types, convert everything to plain float
    return {k: float(v) if v is not None else 0.0 for k, v in row.items()}


def run_pipeline(customer_unique_id: str) -> dict:
    """Run all 5 agents in sequence and return the final report."""
    start_time = datetime.now()
    logger.info(f"Pipeline starting for customer: {customer_unique_id[:8]}...")

    report = {
        "customer_id": customer_unique_id,
        "timestamp":   start_time.isoformat(),
        "agents_run":  []
    }

    # Step 1 - get order history from BigQuery
    logger.info("Agent 1/5: Fetching order history ...")
    try:
        order_history = run_query(
            "customer_order_history",
            {"customer_unique_id": customer_unique_id}
        )
        report["order_history"]      = order_history
        report["total_orders_found"] = len(order_history)
        report["agents_run"].append("DataQueryAgent ?")
        logger.success(f"Agent 1 done: {len(order_history)} orders found")
    except Exception as e:
        logger.error(f"Agent 1 failed: {e}")
        report["agents_run"].append("DataQueryAgent ?")
        order_history = []

    # Step 2 - score churn probability via the prediction API
    logger.info("Agent 2/5: Scoring churn risk ...")
    try:
        features = get_customer_features(customer_unique_id)
        if not features:
            raise ValueError("Customer not found in feature_customer_360")

        pred_response = requests.post(PREDICT_URL, json=features)
        prediction    = pred_response.json()

        report["churn_probability"] = prediction["churn_probability"]
        report["risk_level"]        = prediction["risk_level"]
        report["top_risk_factors"]  = prediction["top_risk_factors"]
        report["shap_values"]       = prediction["shap_values"]
        report["agents_run"].append("PredictionAgent ?")
        logger.success(
            f"Agent 2 done: churn={prediction['churn_probability']:.0%}, "
            f"risk={prediction['risk_level']}"
        )
    except Exception as e:
        logger.error(f"Agent 2 failed: {e}")
        report["agents_run"].append("PredictionAgent ?")
        prediction = {"churn_probability": 0, "risk_level": "UNKNOWN",
                      "top_risk_factors": [], "shap_values": {}}

    # Step 3 - ask Gemini to explain the SHAP values in plain English
    logger.info("Agent 3/5: Generating root-cause explanation ...")
    try:
        shap_explanation = explain_churn_score(features, customer_id=customer_unique_id)
        report["shap_explanation"] = shap_explanation
        report["agents_run"].append("RootCauseAgent ?")
        logger.success("Agent 3 done: explanation generated")
    except Exception as e:
        logger.error(f"Agent 3 failed: {e}")
        report["agents_run"].append("RootCauseAgent ?")
        shap_explanation = "Explanation unavailable."

    # Step 4 - compare this customer against their state cohort
    logger.info("Agent 4/5: Benchmarking vs cohort ...")
    try:
        benchmark = get_cohort_benchmark(customer_unique_id)
        report["benchmark"] = benchmark
        report["agents_run"].append("BenchmarkAgent ?")
        logger.success(f"Agent 4 done: cohort state={benchmark.get('state')}, "
                       f"size={benchmark.get('cohort_size'):,}")
    except Exception as e:
        logger.error(f"Agent 4 failed: {e}")
        report["agents_run"].append("BenchmarkAgent ?")
        benchmark = {}

    # Step 5 - generate targeted retention actions using Gemini
    logger.info("Agent 5/5: Generating retention recommendations ...")
    try:
        recommendations = generate_recommendations(
            churn_probability = prediction["churn_probability"],
            risk_level        = prediction["risk_level"],
            top_risk_factors  = prediction["top_risk_factors"],
            benchmark         = benchmark,
            shap_explanation  = shap_explanation
        )
        report["recommendations"] = recommendations
        report["agents_run"].append("RecommendationAgent ?")
        logger.success("Agent 5 done: recommendations generated")
    except Exception as e:
        logger.error(f"Agent 5 failed: {e}")
        report["agents_run"].append("RecommendationAgent ?")
        recommendations = "Recommendations unavailable."

    elapsed = (datetime.now() - start_time).total_seconds()
    report["elapsed_seconds"] = round(elapsed, 2)
    logger.success(f"Pipeline complete in {elapsed:.1f}s")
    return report


def print_report(report: dict):
    divider = "=" * 60

    print(f"\n{divider}")
    print(f"  RETAILPULSE CHURN RISK REPORT")
    print(f"  Customer: ...{report['customer_id'][-12:]}")
    print(f"  Generated: {report['timestamp'][:19]}")
    print(f"{divider}")

    prob = report.get('churn_probability', 0)
    risk = report.get('risk_level', 'UNKNOWN')
    bar  = "¦" * int(prob * 20) + "¦" * (20 - int(prob * 20))
    print(f"\nCHURN SCORE")
    print(f"  [{bar}] {prob:.0%}  ({risk} RISK)")

    print(f"\nORDER HISTORY ({report.get('total_orders_found', 0)} orders found)")
    for order in report.get('order_history', [])[:3]:
        print(f"  {order.get('order_date')} | {order.get('order_status'):12s} | "
              f"R${order.get('payment_value')} | "
              f"Delivery: {order.get('delivery_days_actual')} days | "
              f"Review: {order.get('review_score')}")

    print(f"\nROOT CAUSE")
    print(f"  {report.get('shap_explanation', 'N/A')}")

    print(f"\nTOP RISK FACTORS")
    for f in report.get('top_risk_factors', []):
        sign = "+" if f['shap_value'] > 0 else "-"
        print(f"  [{sign}] {f['feature']:30s} SHAP={f['shap_value']:+.3f}")

    bm = report.get('benchmark', {})
    if bm:
        print(f"\nCOHORT BENCHMARK (State: {bm.get('state')}, n={bm.get('cohort_size'):,})")
        print(f"  Avg delivery : {bm.get('cust_avg_delivery')} days "
              f"(cohort avg: {bm.get('cohort_avg_delivery')} days, "
              f"diff: {bm.get('delivery_vs_cohort'):+.1f})")
        print(f"  Review score : {bm.get('cust_avg_review')} "
              f"(cohort avg: {bm.get('cohort_avg_review')}, "
              f"diff: {bm.get('review_vs_cohort'):+.2f})")

    print(f"\nRETENTION RECOMMENDATIONS")
    for line in report.get('recommendations', '').split('\n'):
        if line.strip():
            print(f"  {line}")

    print(f"\nAgents: {' -> '.join(report.get('agents_run', []))}")
    print(f"Total time: {report.get('elapsed_seconds', 0):.1f}s")
    print(f"{divider}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailPulse Churn Risk Pipeline")
    parser.add_argument("--customer", type=str, default=None,
                        help="customer_unique_id to analyze")
    args = parser.parse_args()

    if args.customer:
        customer_id = args.customer
    else:
        logger.info("No customer ID provided, picking a random one from BigQuery...")
        sample = list(client.query("""
            SELECT customer_unique_id
            FROM `retailpulse-509504.retailpulse_mart.feature_customer_360`
            WHERE avg_delivery_days IS NOT NULL
            LIMIT 1
        """).result())[0]
        customer_id = sample['customer_unique_id']
        logger.info(f"Selected customer: {customer_id[:8]}...")

    report = run_pipeline(customer_id)
    print_report(report)

    output_path = f"reports/report_{customer_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("reports", exist_ok=True)
    with open(output_path, "w") as f:
        if 'benchmark' in report:
            report['benchmark'] = {
                k: (str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v)
                for k, v in report['benchmark'].items()
            }
        json.dump(report, f, indent=2, default=str)
    logger.success(f"Report saved to {output_path}")
